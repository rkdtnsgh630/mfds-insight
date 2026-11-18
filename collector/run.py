"""수집 실행 진입점.

사용 예:
  MFDS_SERVICE_KEY=... python -m collector.run --apis tier:core
  MFDS_SERVICE_KEY=... python -m collector.run --apis drug_permit,gmp --max-pages 1

인증키는 환경변수로만 받는다. 명령행 인자·로그·DB에 기록하지 않는다.
"""

import argparse
import json
import math
import os
import sys
import urllib.parse
from datetime import datetime, timedelta

from . import store
from .apis import APIS, select_apis
from .client import ApiError, Client


def _redact(text, client):
    key = getattr(client, "key", "") or ""
    if key:
        for form in (key, urllib.parse.quote_plus(key), urllib.parse.quote(key, safe="")):
            text = text.replace(form, "[KEY]")
    return text


def _summary(api, ar, status, note, total, pages, error):
    s = ar.stats
    return {"api_id": api["id"], "name": api["name"], "status": status, "total": total, "pages": pages,
            "fetched": s["fetched"], "added": s["added"], "updated": s["updated"], "removed": s["removed"],
            "reappeared": s["reappeared"], "duplicates": s["duplicates"], "key_collisions": s["key_collisions"],
            "note": note, "error": error}


def since_date(last_started, lookback_days):
    """'2026-11-17T22:51:56Z', 7 -> '20261110'"""
    d = datetime.strptime(last_started[:10], "%Y-%m-%d") - timedelta(days=lookback_days)
    return d.strftime("%Y%m%d")


def collect_incremental(con, client, run_id, api, rows):
    """변경분만 수집한다 (apis.py의 incremental 설정). 결측 판정은 하지 않는다."""
    inc = api["incremental"]
    since = since_date(store.last_success_started(con, api["id"]), inc.get("lookback_days", 7))
    ar = store.ApiRun(con, run_id, api)
    total = pages = 0
    error = None
    notes = [f"증분 수집: {inc['since_param']}={since} 이후 변경분"]
    try:
        page = 1
        while True:
            t, items = client.get_page(api["path"], page, rows, params={inc["since_param"]: since})
            if page == 1:
                total = t
            ar.add_records(items)
            con.commit()
            pages = page
            if page >= math.ceil(total / rows):  # total=0이면 0페이지 → 바로 끝
                break
            if not items:
                error = f"빈 페이지 {page} (totalCount {total})"
                break
            page += 1
        if not error and inc.get("new_keys_from"):
            limit = inc.get("max_new", 300)
            keys = store.missing_keys(con, inc["new_keys_from"], api["id"], limit + 1)
            not_found = 0
            for k in keys[:limit]:
                _, items = client.get_page(api["path"], 1, 10, params={inc["id_param"]: k})
                if not items:
                    not_found += 1
                ar.add_records(items)
            con.commit()
            if keys:
                notes.append(f"신규 품목 개별 요청 {min(len(keys), limit)}건 (조회 안 됨 {not_found}건)"
                             + (f", 한도 {limit}건 초과분은 다음 실행에" if len(keys) > limit else ""))
    except ApiError as e:
        error = f"[{e.code}] {e}" if e.code else str(e)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    if error:
        error = _redact(error, client)
    status, note = ar.finish(False, total, pages, error, incremental=True, extra_notes=notes)
    return _summary(api, ar, status, note, total, pages, error)


def collect_api(con, client, run_id, api, rows, max_pages=None, full=False):
    """한 API를 페이지 끝까지(또는 max_pages까지) 수집하고 결과 요약을 돌려준다.

    증분 설정이 있는 API는 기준선이 있고 full·max_pages가 아니면 변경분만 받는다.
    """
    if api.get("incremental") and not full and not max_pages and store.has_complete_run(con, api["id"]):
        return collect_incremental(con, client, run_id, api, rows)
    ar = store.ApiRun(con, run_id, api)
    total = 0
    pages = 0
    complete = False
    error = None
    try:
        page = 1
        while True:
            t, items = client.get_page(api["path"], page, rows)
            if page == 1:
                total = t
            ar.add_records(items)
            con.commit()
            pages = page
            expected = math.ceil(total / rows) if total else 0
            if page >= expected:
                complete = True
                break
            if not items:
                error = f"빈 페이지 {page} (예상 {expected}페이지, totalCount {total})"
                break
            if max_pages and page >= max_pages:
                break
            page += 1
    except ApiError as e:
        error = f"[{e.code}] {e}" if e.code else str(e)
    except Exception as e:  # 예기치 못한 오류도 실행 이력에 남긴다
        error = f"{type(e).__name__}: {e}"
    if error:
        error = _redact(error, client)
    status, note = ar.finish(complete, total, pages, error)
    return _summary(api, ar, status, note, total, pages, error)


def render_markdown(run_id, results, calls):
    lines = [f"## 수집 결과 (run {run_id}, API 호출 {calls}회)", "",
             "| API | 상태 | totalCount | 수집 | 추가 | 변경 | 결측 | 키충돌 | 비고 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        memo = r["error"] or r["note"] or ""
        lines.append(f"| {r['name']} (`{r['api_id']}`) | {r['status']} | {r['total']} | {r['fetched']} | "
                     f"{r['added']} | {r['updated']} | {r['removed']} | {r['key_collisions']} | {memo} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description="MFDS 공공데이터 수집기")
    p.add_argument("--db", default="data/mfds.sqlite")
    p.add_argument("--apis", default="tier:core", help="tier:core | tier:hold | tier:core+hold | all | id1,id2")
    p.add_argument("--full", action="store_true", help="증분 설정이 있는 API도 전체 수집 (결측 점검, 월 1회)")
    p.add_argument("--rows", type=int, default=500, help="페이지당 건수")
    p.add_argument("--max-pages", type=int, default=0, help="API당 최대 페이지 (0=전체, 시험용)")
    p.add_argument("--sleep", type=float, default=0.1, help="호출 간 대기(초)")
    p.add_argument("--trigger", default="manual")
    p.add_argument("--summary", default="", help="결과 요약 JSON 저장 경로")
    args = p.parse_args(argv)

    key = os.environ.get("MFDS_SERVICE_KEY", "")
    if not key.strip():
        print("오류: 환경변수 MFDS_SERVICE_KEY가 설정되지 않았습니다.", file=sys.stderr)
        return 1
    try:
        apis = select_apis(args.apis)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    db_dir = os.path.dirname(args.db)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    con = store.connect(args.db)
    store.register_apis(con, APIS)
    client = Client(key, sleep=args.sleep)
    selection = (args.apis + (f" max_pages={args.max_pages}" if args.max_pages else "")
                 + (" full" if args.full else ""))
    migrated = 0
    for api in apis:
        n = store.migrate_dropped_fields(con, api)
        if n:
            print(f"[migrate ] {api['id']:20} 저장 안 하는 필드 삭제 {n}건 (변경 이력 미기록)", flush=True)
        migrated += n
    run_id = store.start_run(con, args.trigger, selection)

    results = []
    for api in apis:
        r = collect_api(con, client, run_id, api, args.rows, args.max_pages or None, full=args.full)
        results.append(r)
        print(f"[{r['status']:8}] {r['api_id']:20} total={r['total']} fetched={r['fetched']} "
              f"+{r['added']} ~{r['updated']} -{r['removed']}" + (f"  ! {r['error']}" if r["error"] else ""),
              flush=True)

    statuses = {r["status"] for r in results}
    if statuses <= {"complete", "incremental"}:
        run_status = "complete"
    else:
        run_status = "failed" if statuses == {"failed"} else "partial"
    store.finish_run(con, run_id, run_status, client.calls)
    if migrated:
        con.execute("VACUUM")  # 지운 필드만큼 파일 크기를 실제로 줄인다
        print(f"VACUUM 완료 (필드 삭제 {migrated}건)", flush=True)
    con.close()

    md = render_markdown(run_id, results, client.calls)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(md)
    if args.summary:
        with open(args.summary, "w", encoding="utf-8") as f:
            json.dump({"run_id": run_id, "status": run_status, "api_calls": client.calls,
                       "selection": selection, "results": results}, f, ensure_ascii=False, indent=2)
    print(f"실행 {run_id}: {run_status}, API 호출 {client.calls}회")
    return 2 if run_status == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
