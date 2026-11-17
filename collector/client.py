"""공공데이터포털(apis.data.go.kr) 호출 클라이언트.

- 표준 라이브러리만 사용한다.
- 인증키는 오류 메시지·로그에 절대 포함하지 않는다 (URL을 출력하지 않음).
- 응답 구조 차이를 흡수한다: items가 flat 배열 / {"item":{}} 래핑 / {"item":[...]} 딕셔너리 / XML.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE_URL = "https://apis.data.go.kr/1471000/"
OK_CODES = {"00", "0", "000"}
NO_DATA_CODES = {"03"}
# 01 APPLICATION_ERROR, 02 DB_ERROR, 04 HTTP_ERROR, 05 SERVICETIMEOUT, 99 UNKNOWN
RETRY_CODES = {"01", "02", "04", "05", "99"}


class ApiError(Exception):
    def __init__(self, message, code=None, retryable=False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def normalize_key(raw):
    """포털의 Encoding/Decoding 키 어느 쪽을 넣어도 동작하도록 디코딩된 형태로 맞춘다."""
    raw = (raw or "").strip()
    if "%" in raw:
        raw = urllib.parse.unquote(raw)
    return raw


def normalize_items(items):
    if items is None or items == "" or items == []:
        return []
    if isinstance(items, dict):
        inner = items.get("item", [])
        items = inner if isinstance(inner, list) else [inner]
    out = []
    for it in items:
        if isinstance(it, dict) and list(it.keys()) == ["item"] and isinstance(it["item"], dict):
            out.append(it["item"])
        elif isinstance(it, dict):
            out.append(it)
    return out


def _to_int(value):
    try:
        return int(str(value).strip() or 0)
    except ValueError:
        return 0


def parse_response(text):
    """응답 본문을 (resultCode, resultMsg, totalCount, items)로 변환한다."""
    text = (text or "").strip()
    if text.startswith("{"):
        data = json.loads(text)
        if "OpenAPI_ServiceResponse" in data:
            h = data["OpenAPI_ServiceResponse"].get("cmmMsgHeader", {}) or {}
            raise ApiError(f"{h.get('errMsg')} ({h.get('returnAuthMsg')})", code=str(h.get("returnReasonCode")))
        root = data.get("response", data)
        header = root.get("header") or {}
        body = root.get("body") or {}
        return (str(header.get("resultCode", "")), header.get("resultMsg", ""),
                _to_int(body.get("totalCount")), normalize_items(body.get("items")))
    if text.startswith("<"):
        root = ET.fromstring(text)
        if root.tag == "OpenAPI_ServiceResponse":
            raise ApiError(f"{root.findtext('.//errMsg')} ({root.findtext('.//returnAuthMsg')})",
                           code=root.findtext(".//returnReasonCode"))
        code = root.findtext(".//header/resultCode") or ""
        msg = root.findtext(".//header/resultMsg") or ""
        total = _to_int(root.findtext(".//body/totalCount"))
        items = [{c.tag: (c.text or "") for c in item} for item in root.iter("item")]
        return code, msg, total, items
    raise ApiError("알 수 없는 응답 형식: " + text[:80], retryable=True)


class Client:
    def __init__(self, service_key, timeout=60, retries=4, sleep=0.1, opener=None, sleeper=time.sleep):
        self.key = normalize_key(service_key)
        if not self.key:
            raise ValueError("인증키가 비어 있습니다 (환경변수 MFDS_SERVICE_KEY)")
        self.timeout = timeout
        self.retries = retries
        self.sleep = sleep
        self._open = opener or urllib.request.urlopen
        self._sleeper = sleeper
        self.calls = 0

    def _url(self, path, params):
        query = urllib.parse.urlencode({"serviceKey": self.key, **params})
        return BASE_URL + path + "?" + query

    def get_page(self, path, page_no, rows):
        """한 페이지를 가져와 (totalCount, items)를 돌려준다. 실패 시 ApiError."""
        url = self._url(path, {"pageNo": page_no, "numOfRows": rows, "type": "json"})
        last_error = None
        for attempt in range(self.retries + 1):
            if attempt:
                self._sleeper(min(2 ** attempt, 30))
            try:
                self.calls += 1
                req = urllib.request.Request(url, headers={"User-Agent": "mfds-insight-collector/0.1"})
                with self._open(req, timeout=self.timeout) as resp:
                    text = resp.read().decode("utf-8", errors="replace")
                code, msg, total, items = parse_response(text)
                if code in NO_DATA_CODES:
                    return 0, []
                if code not in OK_CODES:
                    raise ApiError(f"resultCode={code} {msg}", code=code, retryable=code in RETRY_CODES)
                if self.sleep:
                    self._sleeper(self.sleep)
                return total, items
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
                portal_error = None
                try:
                    parse_response(body)
                except ApiError as ae:
                    portal_error = ae
                except Exception:
                    pass
                if portal_error is not None and portal_error.code:
                    # 포털 인증 오류 (예: 30 미등록 키, 22 한도 초과) — 재시도해도 소용없음
                    raise ApiError(f"HTTP {e.code}: {portal_error}", code=portal_error.code) from None
                last_error = ApiError(f"HTTP {e.code}", code=f"HTTP{e.code}",
                                      retryable=e.code >= 500 or e.code == 429)
            except ApiError as e:
                last_error = e
            except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError, ET.ParseError) as e:
                last_error = ApiError(f"{type(e).__name__}: {e}", retryable=True)
            if not last_error.retryable:
                raise last_error
        raise last_error
