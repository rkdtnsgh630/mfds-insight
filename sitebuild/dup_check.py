"""생산·수입실적에서 같은 품목·연도·구분(ITEM_SEQ|DATE_YEAR|RESULT_PART)에 행이 여러 개인 경우를 비교한다.

수집기는 키가 겹치면 두 번째 행을 '키#해시'로 따로 보관한다 (collector/store.py).
이 스크립트는 그 묶음마다 어떤 필드가 다른지 세고 예시를 보여 준다. DB 읽기만 한다.

사용: python -m sitebuild.dup_check --db data/mfds.sqlite [--summary 파일]
"""

import argparse
import json
import sqlite3
from collections import Counter, defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/mfds.sqlite")
    ap.add_argument("--summary")
    ap.add_argument("--api", default="production_import")
    args = ap.parse_args()
    con = sqlite3.connect(args.db)
    rows = con.execute("SELECT record_key, payload FROM raw_record WHERE api_id=? AND is_present=1", (args.api,)).fetchall()
    groups = defaultdict(list)
    for key, payload in rows:
        groups[key.split("#")[0]].append(json.loads(payload))
    dup = {k: v for k, v in groups.items() if len(v) > 1}
    size = Counter(len(v) for v in dup.values())
    diff_fields = Counter()
    same_amt = 0
    pattern = Counter()
    for k, recs in dup.items():
        keys = sorted({f for r in recs for f in r})
        diffs = tuple(f for f in keys if len({json.dumps(r.get(f), ensure_ascii=False) for r in recs}) > 1)
        diff_fields.update(diffs)
        pattern[diffs] += 1
        if len({str(r.get("AMT")) for r in recs}) == 1:
            same_amt += 1
    years = Counter(k.split("|")[1] for k in dup)
    parts = Counter(k.split("|")[2] for k in dup if k.count("|") >= 2)
    out = [f"## {args.api} 키 중복 점검", "",
           f"- 전체 행 {len(rows)}, 키 묶음 {len(groups)}, **같은 키에 2행 이상인 묶음 {len(dup)}개**",
           f"- 묶음 크기: " + ", ".join(f"{n}행 {c}개" for n, c in sorted(size.items())),
           f"- AMT(금액)까지 같은 묶음: {same_amt}개",
           f"- 연도별: " + ", ".join(f"{y} {c}" for y, c in sorted(years.items())),
           f"- 구분별: " + ", ".join(f"{p} {c}" for p, c in parts.items()),
           "", "### 서로 다른 필드 (묶음 수)", "", "| 필드 | 묶음 수 |", "|---|---|"]
    out += [f"| {f} | {c} |" for f, c in diff_fields.most_common()]
    out += ["", "### 다른 필드 조합 (상위 10)", "", "| 다른 필드 | 묶음 수 |", "|---|---|"]
    out += [f"| {', '.join(p) or '(없음: 완전 동일)'} | {c} |" for p, c in pattern.most_common(10)]
    out += ["", "### 예시 (조합별 2개)", ""]
    shown = Counter()
    for k, recs in dup.items():
        keys = sorted({f for r in recs for f in r})
        diffs = tuple(f for f in keys if len({json.dumps(r.get(f), ensure_ascii=False) for r in recs}) > 1)
        if shown[diffs] >= 2 or pattern[diffs] < 2 and shown[diffs] >= 1:
            continue
        shown[diffs] += 1
        out.append(f"- `{k}`")
        for r in recs:
            out.append("  - " + " · ".join(f"{f}={r.get(f)}" for f in (["ITEM_NAME", "ENTP_NAME", "AMT"] + [d for d in diffs if d not in ("ITEM_NAME", "ENTP_NAME", "AMT")])))
        if sum(shown.values()) >= 16:
            break
    text = "\n".join(out) + "\n"
    print(text)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
