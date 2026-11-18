#!/usr/bin/env bash
# Release(data-latest)의 최신 화면용 데이터를 받아 Claude 아티팩트 게시용 폴더(dist/)를 만든다.
# 사용: tools/prepare_artifact.sh <이전 meta.json 경로 또는 빈 값>
#   종료 코드 0  = dist/ 준비 완료 (게시 필요)
#   종료 코드 10 = 새 데이터 없음 (게시 불필요)
#   그 외       = 오류 (게시하지 말 것)
set -euo pipefail
cd "$(dirname "$0")/.."
PREV_META="${1:-}"
BASE="https://github.com/rkdtnsgh630/mfds-insight/releases/download/data-latest"

rm -rf dist work && mkdir -p dist work
curl -fsSL --retry 3 -o work/site-data.tar.gz "$BASE/site-data.tar.gz"
tar -xzf work/site-data.tar.gz -C work

# 필수 파일 점검
for f in meta.json dashboard.json companies_index.json drugs_index.json; do
  [ -s "work/data/$f" ] || { echo "오류: data/$f 없음"; exit 2; }
done
n_comp=$(ls work/data/companies | wc -l); n_drug=$(ls work/data/drugs | wc -l)
[ "$n_comp" -ge 50 ] && [ "$n_drug" -ge 50 ] || { echo "오류: 분할 파일 수 부족 ($n_comp/$n_drug)"; exit 2; }

NEW_GEN=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["generated_at"])' work/data/meta.json)
if [ -n "$PREV_META" ] && [ -s "$PREV_META" ]; then
  python3 - "$PREV_META" work/data/meta.json <<'PY' || exit $?
import json, sys
p, n = (json.load(open(x)) for x in sys.argv[1:3])
pc = {a["id"]: a["count"] for a in p["apis"]}
for a in n["apis"]:
    old = pc.get(a["id"])
    if old and a["count"] < old * 0.9:
        print(f"오류: {a['id']} 건수 급감 {old} -> {a['count']}"); sys.exit(3)
if n["generated_at"] <= p["generated_at"]:
    print(f"새 데이터 없음 (generated_at {n['generated_at']})"); sys.exit(10)
PY
fi

cp site/index.html site/app.js site/style.css site/world.json dist/
cp -r work/data dist/data
# 게시할 파일 목록 (index.html 제외, dist 기준 상대경로)
( cd dist && find . -type f ! -name index.html | sed 's|^\./||' | sort ) > work/files.txt
echo "준비 완료: generated_at=$NEW_GEN, 파일 $(wc -l < work/files.txt)개"
