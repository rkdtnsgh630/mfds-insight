"""요청변수 동작 확인용 시험 호출 (수집 DB에는 쓰지 않음).

제품허가 상세 API의 변경일자·품목기준코드 필터가 실제로 동작하는지, 응답 크기가
어느 필드에서 나오는지 확인한다. 결과는 마크다운으로 출력한다 (GitHub 단계 요약용).
인증키·요청 URL은 출력하지 않는다.

사용: MFDS_SERVICE_KEY=... python -m collector.probe [--summary 파일]
"""

import argparse
import json
import os
import sys
import time
import urllib.request

from .client import ApiError, Client, parse_response

LIST = "DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnInq08"
DETAIL = "DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnDtlInq08"


def fetch(client, path, params):
    """(초, 응답 바이트, totalCount, items, 오류)"""
    url = client._url(path, {"type": "json", **params})
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "mfds-insight-probe/0.1"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        code, msg, total, items = parse_response(text)
        err = None if code in ("00", "0", "000", "03") else f"resultCode={code} {msg}"
        return time.time() - t0, len(text.encode("utf-8")), total, items, err
    except ApiError as e:
        return time.time() - t0, 0, 0, [], f"[{e.code}] {e}"
    except Exception as e:  # 시험 호출이므로 오류 내용만 기록하고 계속
        return time.time() - t0, 0, 0, [], f"{type(e).__name__}"


def field_sizes(items, top=10):
    sizes = {}
    for it in items:
        for k, v in it.items():
            sizes[k] = sizes.get(k, 0) + len(json.dumps(v, ensure_ascii=False).encode("utf-8"))
    total = sum(sizes.values()) or 1
    rows = sorted(sizes.items(), key=lambda kv: -kv[1])[:top]
    return [(k, v / max(len(items), 1), v * 100 / total) for k, v in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary")
    args = ap.parse_args()
    client = Client(os.environ.get("MFDS_SERVICE_KEY", ""))
    out = ["## 요청변수 시험 호출 결과", ""]

    def row(label, path, params, show_dates=True):
        sec, size, total, items, err = fetch(client, path, params)
        dates = sorted(d for d in (str(i.get("CHANGE_DATE") or "") for i in items) if d)
        empty = sum(1 for i in items if not str(i.get("CHANGE_DATE") or "").strip())
        rng = f"{dates[0]} ~ {dates[-1]}" if dates else "-"
        p = ", ".join(f"{k}={v}" for k, v in params.items() if k not in ("pageNo",))
        out.append(f"| {label} | `{p}` | {err or 'OK'} | {total} | {len(items)} | {sec:.1f} | "
                   f"{size / 1024:.0f} | {rng if show_dates else '-'} | {empty if show_dates else '-'} |")
        return items

    out += ["| 시험 | 요청변수 | 결과 | totalCount | 받은 건수 | 초 | KB | CHANGE_DATE 범위 | CHANGE_DATE 빈 값 |",
            "|---|---|---|---|---|---|---|---|---|"]
    lst = row("목록 100건", LIST, {"pageNo": 1, "numOfRows": 100}, show_dates=False)
    det = row("상세 100건 (필터 없음)", DETAIL, {"pageNo": 1, "numOfRows": 100})
    row("상세 변경일 11/01~11/18 (YYYYMMDD)", DETAIL,
        {"pageNo": 1, "numOfRows": 500, "start_change_date": "20261101", "end_change_date": "20261118"})
    row("상세 변경일 11/01~11/18 (YYYY-MM-DD)", DETAIL,
        {"pageNo": 1, "numOfRows": 500, "start_change_date": "2026-11-01", "end_change_date": "2026-11-18"})
    row("상세 변경일 시작만 20261101", DETAIL, {"pageNo": 1, "numOfRows": 500, "start_change_date": "20261101"})
    row("상세 변경일 10/01~10/31", DETAIL,
        {"pageNo": 1, "numOfRows": 500, "start_change_date": "20261001", "end_change_date": "20261031"})
    row("상세 허가일 2026", DETAIL, {"pageNo": 1, "numOfRows": 500, "item_permit_date": "2026"})
    seqs = [str(i.get("ITEM_SEQ")) for i in lst[:3] if i.get("ITEM_SEQ")]
    for s in seqs[:2]:
        row(f"상세 품목기준코드 {s}", DETAIL, {"pageNo": 1, "numOfRows": 10, "item_seq": s})

    out += ["", "### 상세 응답에서 용량이 큰 필드 (100건 기준)", "",
            "| 필드 | 건당 평균 바이트 | 비중 % |", "|---|---|---|"]
    out += [f"| {k} | {avg:.0f} | {pct:.1f} |" for k, avg, pct in field_sizes(det)]
    out += ["", "### 목록 응답에서 용량이 큰 필드 (100건 기준)", "",
            "| 필드 | 건당 평균 바이트 | 비중 % |", "|---|---|---|"]
    out += [f"| {k} | {avg:.0f} | {pct:.1f} |" for k, avg, pct in field_sizes(lst, top=5)]
    text = "\n".join(out) + "\n"
    print(text)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    sys.exit(main())
