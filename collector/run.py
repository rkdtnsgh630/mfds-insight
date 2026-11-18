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

from . import store
from .apis import APIS, select_apis
from .client import ApiError, Client


def _redact(text, client):
    key = getattr(client, "key", "") or ""
    if key:
        for form in (key, urllib.parse.quote_plus(key), urllib.parse.quote(key, safe="")):
            text = text.replace(form, "[KEY]")
    return text


def collect_api(con, client, run_id, api, rows, max_pages=None):
    """한 API를 페이지 끝까지(또는 max_pages까지) 수집하고 결과 요약을 돌려준다."""
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
    s = ar.stats
    return {"api_id": api["id"], "name": api["name"], "status": status, "total": total, "pages": pages,
            "fetched": s["fetched"], "added": s["added"], "updated": s["updated"], "removed": s["removed"],
            "reappeared": s["reappeared"], "duplicates": s["duplicates"], "key_collisions": s["key_collisions"],
            "note": note, "error": error}


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
    p.add_argument("--apis", default="tier:core", help="tier:core | tier:slow | tier:hold | tier:core+slow | all | id1,id2")
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
    selection = args.apis + (f" max_pages={args.max_pages}" if args.max_pages else "")
    run_id = store.start_run(con, args.trigger, selection)

    results = []
    for api in apis:
        r = collect_api(con, client, run_id, api, args.rows, args.max_pages or None)
        results.append(r)
        print(f"[{r['status']:8}] {r['api_id']:20} total={r['total']} fetched={r['fetched']} "
              f"+{r['added']} ~{r['updated']} -{r['removed']}" + (f"  ! {r['error']}" if r["error"] else ""),
              flush=True)

    statuses = {r["status"] for r in results}
    run_status = "complete" if statuses == {"complete"} else ("failed" if statuses == {"failed"} else "partial")
    store.finish_run(con, run_id, run_status, client.calls)
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
