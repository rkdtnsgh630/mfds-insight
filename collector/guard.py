"""게시 전 보관 점검: 새 DB가 이전 DB의 기록을 잃지 않았는지 확인한다.

이 프로젝트는 API에서 빠진 기록도 지우지 않고 보관한다 (사용자 결정 2026-11-18).
그러므로 API별 원본 행 수(raw_record, 제공 여부와 무관)와 변경 이력 수는 줄어들 수 없다.
하나라도 줄었으면 오류로 끝내서 Release의 DB를 덮어쓰지 못하게 한다.

사용: python -m collector.guard --prev data/prev.sqlite --new data/mfds.sqlite [--summary 파일]
"""

import argparse
import sqlite3
import sys


def counts(path):
    con = sqlite3.connect(path)
    try:
        raw = dict(con.execute("SELECT api_id, COUNT(*) FROM raw_record GROUP BY api_id").fetchall())
        logs = con.execute("SELECT COUNT(*) FROM change_log").fetchone()[0]
        runs = con.execute("SELECT COUNT(*) FROM collect_run").fetchone()[0]
    finally:
        con.close()
    return raw, logs, runs


def check(prev_path, new_path):
    """(통과 여부, 마크다운 줄 목록)"""
    p_raw, p_log, p_run = counts(prev_path)
    n_raw, n_log, n_run = counts(new_path)
    ok = True
    lines = ["## 보관 점검 (게시 전)", "", "| 데이터 | 이전 | 이번 | 결과 |", "|---|---|---|---|"]
    for api in sorted(set(p_raw) | set(n_raw)):
        a, b = p_raw.get(api, 0), n_raw.get(api, 0)
        bad = b < a
        ok &= not bad
        lines.append(f"| {api} | {a} | {b} | {'**줄어듦 → 게시 중단**' if bad else '통과'} |")
    for name, a, b in (("변경 이력(change_log)", p_log, n_log), ("수집 실행 기록", p_run, n_run)):
        bad = b < a
        ok &= not bad
        lines.append(f"| {name} | {a} | {b} | {'**줄어듦 → 게시 중단**' if bad else '통과'} |")
    return ok, lines


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--summary")
    args = ap.parse_args(argv)
    ok, lines = check(args.prev, args.new)
    text = "\n".join(lines) + "\n"
    print(text)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as f:
            f.write(text)
    if not ok:
        print("오류: 이전 DB보다 기록이 줄었습니다. DB를 게시하지 않습니다.", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
