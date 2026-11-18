"""수집 DB의 API별 실제 필드 목록·채움률·값 형식을 마크다운으로 출력한다 (화면용 데이터 설계 근거).

사용: python -m sitebuild.inspect_db --db data/mfds.sqlite [--summary 파일]
"""

import argparse
import json
import re
import sqlite3
from collections import Counter


def shape(v):
    s = str(v).strip()
    if not s:
        return "(빈 값)"
    s = re.sub(r"[0-9]", "9", s)
    s = re.sub(r"[A-Za-z]", "A", s)
    s = re.sub(r"[가-힣]", "가", s)
    return s[:20]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/mfds.sqlite")
    ap.add_argument("--summary")
    ap.add_argument("--apis", default="")
    args = ap.parse_args()
    con = sqlite3.connect(args.db)
    apis = [a for (a,) in con.execute("SELECT DISTINCT api_id FROM raw_record ORDER BY api_id")]
    if args.apis:
        apis = [a for a in apis if a in args.apis.split(",")]
    out = ["## 수집 DB 필드 점검", ""]
    for api in apis:
        rows = [json.loads(p) for (p,) in con.execute(
            "SELECT payload FROM raw_record WHERE api_id=? AND is_present=1", (api,))]
        n = len(rows)
        fields = Counter()
        for r in rows:
            fields.update(k for k, v in r.items() if str(v if v is not None else "").strip())
        allkeys = sorted({k for r in rows for k in r})
        out += [f"### {api} ({n}건)", "", "| 필드 | 채움 % | 고유값 수 | 형식 상위 | 예시 |", "|---|---|---|---|---|"]
        for k in allkeys:
            vals = [r.get(k) for r in rows]
            filled = fields[k]
            distinct = len({str(v) for v in vals})
            shapes = Counter(shape(v) for v in vals).most_common(3)
            ex = [str(v)[:40] for v in vals if str(v if v is not None else "").strip()][:1]
            if distinct <= 12:
                ex = [f"{v}({c})" for v, c in Counter(str(v)[:30] for v in vals).most_common(8)]
            cell = "; ".join(ex).replace("|", "/").replace("\n", " ")
            sh = ", ".join(f"`{s}`×{c}" for s, c in shapes).replace("|", "/")
            out.append(f"| {k} | {filled * 100 / max(n, 1):.0f} | {distinct} | {sh} | {cell} |")
        out.append("")
    text = "\n".join(out) + "\n"
    print(text)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
