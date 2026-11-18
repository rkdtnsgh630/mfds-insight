"""수집 DB(SQLite)에서 사이트 화면용 JSON을 만든다.

원칙 (docs/DASHBOARD_DESIGN.md):
- 실제 수집 데이터만 쓴다. 값이 없으면 빈 칸으로 두고 추정하지 않는다.
- 업체 연결은 사업자등록번호(BIZRNO), 품목 연결은 품목기준코드(ITEM_SEQ)로만 한다. 이름 유사성으로 묶지 않는다.
- 생산실적 금액은 백만원, 수입실적 금액은 달러(공식 명세). 서로 더하지 않는다.
- 공급중단 신고 중 '공개 동의하지 않음'(OPEN_AGREE_YN_NM)은 화면에 싣지 않는다.

사용: python -m sitebuild.export --db data/mfds.sqlite --out site/data
"""

import argparse
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
SHARDS = 100  # 상세 파일 분할 수 (키 끝 두 자리)

SOURCE = {
    "drug_permit": "15095677", "drug_permit_detail": "15095677", "company_list": "15095682",
    "production_import": "15056880", "admin_action": "15058457", "recall_drug": "15059114",
    "supply_suspend": "15057899", "supply_shortage": "15056886", "gmp": "15097207",
    "overseas_mfr": "15090422", "safety_letter": "15059182",
}

# WHO ATC 해부학적 대분류 (1단계)
ATC1 = {
    "A": "소화기관·대사", "B": "혈액·조혈기관", "C": "심혈관계", "D": "피부", "G": "비뇨생식기·성호르몬",
    "H": "전신 호르몬", "J": "전신 감염", "L": "항암·면역", "M": "근골격계", "N": "신경계",
    "P": "항기생충", "R": "호흡기", "S": "감각기관", "V": "기타",
}

ADMIN_TYPES = [("허가취소", ("허가취소", "허가 취소", "등록취소", "취소")), ("업무정지", ("업무정지", "업무 정지")),
               ("과징금", ("과징금",)), ("경고", ("경고",))]


def v(rec, key):
    """빈 값·'None' 문자열을 ''로 정리한 문자열."""
    x = rec.get(key)
    if x is None:
        return ""
    s = str(x).strip()
    return "" if s in ("None", "null") else s


def ymd(s):
    """YYYYMMDD / YYYY-MM-DD / 14자리 → 'YYYY-MM-DD' 또는 ''."""
    d = re.sub(r"\D", "", s or "")
    if len(d) < 8:
        return ""
    y, m, dd = d[:4], d[4:6], d[6:8]
    if not ("1900" <= y <= "2100" and "01" <= m <= "12" and "01" <= dd <= "31"):
        return ""
    return f"{y}-{m}-{dd}"


def biz(s):
    d = re.sub(r"\D", "", s or "")
    return d if len(d) == 10 else ""


def cut(s, n):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def num(s):
    try:
        return float(str(s).replace(",", ""))
    except ValueError:
        return None


def strip_codes(s):
    return re.sub(r"\[[^\]]*\]", "", s or "").replace("/", ", ").strip(" ,")


def shard(key):
    d = re.sub(r"\D", "", key)
    return d[-2:].zfill(2) if d else "00"


def admin_type(text):
    for name, words in ADMIN_TYPES:
        if any(w in text for w in words):
            return name
    return "기타"


class Exporter:
    def __init__(self, db, out):
        self.con = sqlite3.connect(db)
        self.out = out
        os.makedirs(os.path.join(out, "drugs"), exist_ok=True)
        os.makedirs(os.path.join(out, "companies"), exist_ok=True)
        self.files = {}

    def rows(self, api_id):
        return [json.loads(p) for (p,) in self.con.execute(
            "SELECT payload FROM raw_record WHERE api_id=? AND is_present=1 ORDER BY record_key", (api_id,))]

    def write(self, rel, data):
        path = os.path.join(self.out, rel)
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        self.files[rel] = len(text.encode("utf-8"))

    # ------------------------------------------------------------------
    def run(self):
        con = self.con
        last = con.execute("SELECT MAX(finished_at) FROM collect_run WHERE status='complete'").fetchone()[0]
        as_of_dt = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(KST)
        self.as_of = as_of_dt.strftime("%Y-%m-%d")
        self.since30 = (as_of_dt - timedelta(days=30)).strftime("%Y-%m-%d")

        P = {a: self.rows(a) for a in SOURCE}
        detail = {v(r, "ITEM_SEQ"): r for r in P["drug_permit_detail"]}
        S = lambda r: v(r, "ITEM_SEQ")

        # ---------- 품목 ----------
        drugs = []
        drug_detail = defaultdict(dict)
        items_by_biz = defaultdict(list)
        for r in P["drug_permit"]:
            seq = S(r)
            d = detail.get(seq, {})
            status = v(r, "CANCEL_NAME") or "정상"
            spc = "전문" if v(r, "SPCLTY_PBLC").startswith("전문") else ("일반" if v(r, "SPCLTY_PBLC") else "")
            atc = v(d, "ATC_CODE")
            flags = ("N" if v(d, "NEWDRUG_CLASS_NAME") == "신약" else "") + ("R" if v(d, "RARE_DRUG_YN") == "Y" else "")
            ingr_kr = cut(strip_codes(v(d, "MAIN_ITEM_INGR")), 60)
            row = [seq, v(r, "ITEM_NAME"), v(r, "ENTP_NAME"), biz(v(r, "BIZRNO")), ymd(v(r, "ITEM_PERMIT_DATE")),
                   spc, status, ingr_kr, cut(v(r, "ITEM_INGR_NAME"), 60), atc, flags, v(r, "PERMIT_KIND_CODE"),
                   ymd(v(r, "CANCEL_DATE"))]
            drugs.append(row)
            items_by_biz[row[3]].append([seq, row[1], row[4], spc, status])
            drug_detail[shard(seq)][seq] = {
                "eng": v(r, "ITEM_ENG_NAME"), "permit_no": v(r, "PRDUCT_PRMISN_NO"), "induty": v(r, "INDUTY"),
                "type": v(r, "PRDUCT_TYPE"), "edi": v(r, "EDI_CODE"), "cnsgn": v(d, "CNSGN_MANUF"),
                "narcotic": v(d, "NARCOTIC_KIND_CODE"), "chart": cut(v(d, "CHART"), 300),
                "storage": v(d, "STORAGE_METHOD"), "valid": v(d, "VALID_TERM"), "pack": cut(v(d, "PACK_UNIT"), 200),
                "material": cut(v(d, "MATERIAL_NAME"), 400), "change_date": ymd(v(d, "CHANGE_DATE")),
                "change_hist": cut(v(d, "GBN_NAME"), 400), "reexam": v(d, "REEXAM_TARGET"),
                "reexam_date": v(d, "REEXAM_DATE"), "ingr_eng": v(d, "MAIN_INGR_ENG"),
                "doc_ee": v(d, "EE_DOC_ID"), "doc_ud": v(d, "UD_DOC_ID"), "doc_nb": v(d, "NB_DOC_ID"),
                "has_detail": bool(d),
            }

        # ---------- 관련 이력 (품목·업체 연결) ----------
        rel = defaultdict(lambda: defaultdict(list))  # seq -> kind -> rows
        by_biz = defaultdict(lambda: defaultdict(list))

        recalls = []
        for r in P["recall_drug"]:
            row = [ymd(v(r, "RECALL_COMMAND_DATE")) or ymd(v(r, "RTRVL_CMMND_DT")), v(r, "PRDUCT"), v(r, "ENTRPS"),
                   biz(v(r, "BIZRNO")), S(r), cut(v(r, "RTRVL_RESN"), 200), v(r, "ENFRC_YN")]
            recalls.append(row)
        recalls.sort(key=lambda x: x[0], reverse=True)
        for row in recalls:
            if row[4]:
                rel[row[4]]["recall"].append([row[0], row[5], row[6]])
            if row[3]:
                by_biz[row[3]]["recall"].append([row[0], row[1], row[4], row[5], row[6]])

        suspends = []
        hidden_suspend = 0
        for r in P["supply_suspend"]:
            if v(r, "OPEN_AGREE_YN_NM") == "동의하지않음":
                hidden_suspend += 1
                continue
            row = [ymd(v(r, "REPORT_DATE")), v(r, "ITEM_NAME"), v(r, "ENTP_NAME"), biz(v(r, "BIZRNO")), S(r),
                   v(r, "SUSPEND_REPORT_FLAG"), ymd(v(r, "SUSPEND_DATE")), cut(v(r, "SUSPEND_REASON"), 200),
                   v(r, "REPORT_PGS_CODE"), v(r, "INV_QTY")]
            suspends.append(row)
        suspends.sort(key=lambda x: x[0], reverse=True)
        for row in suspends:
            if row[4]:
                rel[row[4]]["suspend"].append([row[0], row[5], row[6], row[7], row[8]])
            if row[3]:
                by_biz[row[3]]["suspend"].append([row[0], row[1], row[4], row[5], row[6], row[8]])

        shortages = []
        for r in P["supply_shortage"]:
            row = [ymd(v(r, "REPORT_DATE")), v(r, "ITEM_NAME"), v(r, "ENTP_NAME"), biz(v(r, "BIZRNO")), S(r),
                   cut(v(r, "SHORT_SUPPLY_REASON"), 200), ymd(v(r, "SUPPLY_PLAN_DATE")), v(r, "REPORT_PGS_CODE"),
                   cut(v(r, "TREATMENT_INFU"), 200)]
            shortages.append(row)
        shortages.sort(key=lambda x: x[0], reverse=True)
        for row in shortages:
            if row[4]:
                rel[row[4]]["shortage"].append([row[0], row[5], row[6], row[7]])
            if row[3]:
                by_biz[row[3]]["shortage"].append([row[0], row[1], row[4], row[5], row[7]])

        admins = []
        for r in P["admin_action"]:
            disp = v(r, "ADM_DISPS_NAME")
            row = [ymd(v(r, "LAST_SETTLE_DATE")), v(r, "ENTP_NAME"), biz(v(r, "BIZRNO")), cut(v(r, "ITEM_NAME"), 120),
                   v(r, "ITEM_SEQ"), cut(disp, 240), cut(v(r, "BEF_APPLY_LAW"), 200), ymd(v(r, "RLS_END_DATE")),
                   admin_type(disp), v(r, "ADDR")]
            admins.append(row)
        admins.sort(key=lambda x: x[0], reverse=True)
        for row in admins:
            for seq in [s for s in re.split(r"[,\s]+", row[4]) if s]:
                rel[seq]["admin"].append([row[0], row[8], row[5]])
            if row[2]:
                by_biz[row[2]]["admin"].append([row[0], row[3], row[8], row[5], row[7]])

        letters = []
        for r in P["safety_letter"]:
            letters.append([ymd(v(r, "PBANC_YMD")), v(r, "TITLE"), v(r, "CHRG_DEP"), v(r, "ATTACH_FILE_URL"),
                            cut(v(r, "PBANC_CONT"), 300), v(r, "SAFT_LETT_NO")])
        letters.sort(key=lambda x: x[0], reverse=True)

        # 생산·수입 (생산=백만원, 수입=달러)
        prod_item = defaultdict(dict)   # seq -> year -> [part, amt]
        prod_biz = defaultdict(lambda: defaultdict(lambda: {"p": 0.0, "i": 0.0, "np": 0, "ni": 0}))
        prod_year = defaultdict(lambda: {"p": 0.0, "i": 0.0, "np": 0, "ni": 0})
        names_from_prod = defaultdict(Counter)
        for r in P["production_import"]:
            year, part, amt = v(r, "DATE_YEAR"), v(r, "RESULT_PART"), num(v(r, "AMT"))
            if not year or amt is None or part not in ("생산", "수입"):
                continue
            k, n = ("p", "np") if part == "생산" else ("i", "ni")
            b = biz(v(r, "BIZRNO"))
            prod_year[year][k] += amt
            prod_year[year][n] += 1
            if b:
                prod_biz[b][year][k] += amt
                prod_biz[b][year][n] += 1
                names_from_prod[b][v(r, "ENTP_NAME")] += 1
            prod_item[S(r)].setdefault(year, []).append([part, round(amt, 3)])

        gmps = []
        for r in P["gmp"]:
            gmps.append([v(r, "BSSH_NM"), biz(v(r, "BIZRNO")), v(r, "KGMP_BGMP_NAME"), v(r, "GMP_INGR_MM_GROUP_NAME"),
                         v(r, "FCTR_ADDR"), ymd(v(r, "VLD_PRD_YMD"))])
        gmps.sort(key=lambda x: x[5], reverse=True)
        overseas = []
        for r in P["overseas_mfr"]:
            overseas.append([v(r, "BSSH_NM"), biz(v(r, "BIZRNO")), v(r, "MFTR_NM"), v(r, "NATN_CD_NM"),
                             cut(v(r, "MFTR_ADDR"), 120), v(r, "MFTR_PRMSN_NO")])
        for row in gmps:
            if row[1]:
                by_biz[row[1]]["gmp"].append([row[2], row[3], row[4], row[5]])
        for row in overseas:
            if row[1]:
                by_biz[row[1]]["overseas"].append([row[2], row[3], row[5]])

        # 품목 상세에 관련 이력 붙이기
        for seq, kinds in rel.items():
            sh = drug_detail.get(shard(seq), {})
            if seq in sh:
                sh[seq]["rel"] = {k: rows[:50] for k, rows in kinds.items()}
        for seq, years in prod_item.items():
            sh = drug_detail.get(shard(seq), {})
            if seq in sh:
                sh[seq]["prod"] = dict(sorted(years.items()))

        # ---------- 업체 ----------
        lic = defaultdict(list)
        lic_names = defaultdict(Counter)
        names = defaultdict(Counter)
        region = {}
        for r in P["company_list"]:
            b = biz(v(r, "BIZRNO"))
            if not b:
                continue
            lic[b].append([v(r, "INDUTY"), ymd(v(r, "PRMISN_DT")), v(r, "PRMISN_NO")])
            lic_names[b][v(r, "ENTRPS")] += 1  # 대표 상호는 업체허가 목록을 우선
            region.setdefault(b, v(r, "ADRES"))
        for row in drugs:
            if row[3]:
                names[row[3]][row[2]] += 1
        for b, c in names_from_prod.items():
            names[b].update(c)
        for kind, idx in (("recall", 2), ("suspend", 2), ("shortage", 2)):
            src = {"recall": recalls, "suspend": suspends, "shortage": shortages}[kind]
            for row in src:
                if row[3]:
                    names[row[3]][row[idx]] += 0.5
        for row in admins:
            if row[2]:
                names[row[2]][row[1]] += 0.5
                region.setdefault(row[2], row[9])
        for row in gmps + overseas:
            if row[1]:
                names[row[1]][row[0]] += 0.5

        for b, c in lic_names.items():
            names[b].update(c)
        all_biz = set(names) | set(by_biz) | set(items_by_biz) | set(prod_biz)
        all_biz.discard("")
        years = sorted(prod_year)
        latest_year = years[-1] if years else ""
        companies = []
        company_detail = defaultdict(dict)
        for b in sorted(all_biz):
            src_names = lic_names[b] if lic_names.get(b) else names[b]
            nm = src_names.most_common(1)[0][0] if src_names else ""
            items = sorted(items_by_biz.get(b, []), key=lambda x: x[2], reverse=True)
            active = sum(1 for it in items if it[4] == "정상")
            bz = by_biz.get(b, {})
            py = prod_biz.get(b, {})
            ly = py.get(latest_year, {})
            induty = sorted({x[0] for x in lic.get(b, []) if x[0]})
            companies.append([b, nm, region.get(b, ""), active, len(items), round(ly.get("p", 0), 1) if ly else None,
                              round(ly.get("i", 0)) if ly else None, len(bz.get("gmp", [])),
                              len(bz.get("overseas", [])), len(bz.get("admin", [])), len(bz.get("recall", [])),
                              len(bz.get("suspend", [])), len(bz.get("shortage", [])), "·".join(induty)])
            company_detail[shard(b)][b] = {
                "name": nm, "names": [n for n, _ in names[b].most_common(5)], "region": region.get(b, ""),
                "licenses": lic.get(b, []), "items": items,
                "prod": {y: {k: round(x, 3) if isinstance(x, float) else x for k, x in d.items()}
                         for y, d in sorted(py.items())},
                **{k: bz.get(k, [])[:300] for k in ("gmp", "admin", "recall", "suspend", "shortage")},
                "overseas": bz.get("overseas", [])[:300], "overseas_total": len(bz.get("overseas", [])),
            }

        # ---------- 통계 ----------
        permit_year = Counter(row[4][:4] for row in drugs if row[4])
        permit_year_kind = defaultdict(Counter)
        for row in drugs:
            if row[4]:
                permit_year_kind[row[4][:4]][row[11] or "기타"] += 1
        cancel_year = Counter(row[12][:4] for row in drugs if row[12])
        active_rows = [row for row in drugs if row[6] == "정상"]
        spc = Counter(row[5] or "미상" for row in active_rows)
        atc = Counter((row[9][:1] if row[9] else "미상") for row in active_rows)
        ptype = Counter()
        active_set = {row[0] for row in active_rows}
        for sh in drug_detail.values():
            for seq, d in sh.items():
                if seq in active_set:
                    ptype[re.sub(r"^\[\d+\]", "", d.get("type", "")) or "미상"] += 1
        top_p = sorted(((b, d[latest_year]["p"]) for b, d in prod_biz.items() if latest_year in d and d[latest_year]["p"] > 0),
                       key=lambda x: -x[1])[:15]
        top_i = sorted(((b, d[latest_year]["i"]) for b, d in prod_biz.items() if latest_year in d and d[latest_year]["i"] > 0),
                       key=lambda x: -x[1])[:15]
        cname = {c[0]: c[1] for c in companies}
        first_year = max(2000, min((int(y) for y in permit_year if y.isdigit()), default=2000))
        yr_range = [str(y) for y in range(first_year, int(self.as_of[:4]) + 1)]

        def monthly(rows, idx, months=36):
            start = (as_of_dt.replace(day=1) - timedelta(days=31 * (months - 1))).strftime("%Y-%m")
            c = Counter(r[idx][:7] for r in rows if r[idx] and r[idx][:7] >= start)
            keys, cur = [], datetime.strptime(start + "-01", "%Y-%m-%d")
            while cur.strftime("%Y-%m") <= self.as_of[:7]:
                keys.append(cur.strftime("%Y-%m"))
                cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
            return {"x": keys, "y": [c.get(k, 0) for k in keys]}

        def recent(rows, idx):
            return [r for r in rows if r[idx] and self.since30 <= r[idx] <= self.as_of]

        new_permits = sorted([r for r in drugs if r[4] and self.since30 <= r[4] <= self.as_of], key=lambda x: x[4], reverse=True)
        new_cancels = sorted([r for r in drugs if r[12] and self.since30 <= r[12] <= self.as_of], key=lambda x: x[12], reverse=True)

        # ---------- 변경 이력 ----------
        changes = []
        label_keys = ("ITEM_NAME", "PRDUCT", "ENTRPS", "BSSH_NM", "MFTR_NM", "TITLE", "ENTP_NAME")
        for run_id, api_id, key, ctype, oldp, newp, at in con.execute(
                "SELECT run_id, api_id, record_key, change_type, old_payload, new_payload, changed_at FROM change_log"
                " WHERE changed_at >= ? ORDER BY id DESC LIMIT 5000",
                ((as_of_dt - timedelta(days=90)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),)):
            p = json.loads(newp or oldp or "{}")
            label = next((v(p, k) for k in label_keys if v(p, k)), "")
            fields = []
            if ctype == "updated" and oldp and newp:
                o, n = json.loads(oldp), json.loads(newp)
                fields = sorted(k for k in set(o) | set(n) if o.get(k) != n.get(k))[:8]
            kst = datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(KST)
            changes.append([kst.strftime("%Y-%m-%d"), api_id, ctype, key, cut(label, 80), biz(v(p, "BIZRNO")),
                            v(p, "ITEM_SEQ"), fields])
        baseline = {a: d for a, d in con.execute(
            "SELECT api_id, MIN(finished_at) FROM collect_api_run WHERE status='complete' GROUP BY api_id")}

        # ---------- 메타 ----------
        api_meta = []
        for a, did in SOURCE.items():
            name, = con.execute("SELECT name FROM api_source WHERE api_id=?", (a,)).fetchone() or (a,)
            lastok = con.execute("SELECT MAX(finished_at) FROM collect_api_run WHERE api_id=? AND status IN ('complete','incremental')",
                                 (a,)).fetchone()[0]
            api_meta.append({"id": a, "name": name, "count": len(P[a]), "last": lastok, "baseline": baseline.get(a),
                             "url": f"https://www.data.go.kr/data/{did}/openapi.do"})

        meta = {"as_of": self.as_of, "since30": self.since30, "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
                "apis": api_meta, "latest_prod_year": latest_year, "hidden_suspend": hidden_suspend,
                "units": {"prod": "백만원", "import": "달러"}}

        dashboard = {
            "kpi": {
                "items_active": len(active_rows), "items_total": len(drugs),
                "companies_with_items": sum(1 for c in companies if c[4] > 0), "companies_total": len(companies),
                "new_permits_30": len(new_permits), "new_cancels_30": len(new_cancels),
                "recalls_30": len(recent(recalls, 0)), "admins_30": len(recent(admins, 0)),
                "suspends_30": len(recent(suspends, 0)), "shortages_30": len(recent(shortages, 0)),
                "letters_30": len(recent(letters, 0)),
                "recalls_total": len(recalls), "admins_total": len(admins), "suspends_total": len(suspends),
                "shortages_total": len(shortages), "gmp_total": len(gmps), "overseas_total": len(overseas),
                "letters_total": len(letters),
            },
            "new_permits": [[r[0], r[1], r[2], r[3], r[4], r[5], r[11]] for r in new_permits[:15]],
            "new_cancels": [[r[0], r[1], r[2], r[3], r[12], r[6]] for r in new_cancels[:15]],
            "recalls": recalls[:8], "admins": [[r[0], r[1], r[2], r[3], r[8]] for r in admins[:8]],
            "suspends": [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in suspends[:8]],
            "shortages": [[r[0], r[1], r[2], r[3], r[4], r[7]] for r in shortages[:8]],
            "letters": [[r[0], r[1], r[3]] for r in letters[:6]],
            "trend": {"permits": monthly(drugs, 4, 24), "recalls": monthly(recalls, 0, 24),
                      "admins": monthly(admins, 0, 24), "suspends": monthly(suspends, 0, 24)},
            "changes_recent": changes[:12], "changes_total": len(changes),
        }
        stats = {
            "prod_year": {"x": years, "p": [round(prod_year[y]["p"], 1) for y in years],
                          "i": [round(prod_year[y]["i"]) for y in years],
                          "np": [prod_year[y]["np"] for y in years], "ni": [prod_year[y]["ni"] for y in years]},
            "top_prod": [[b, cname.get(b, ""), round(x, 1)] for b, x in top_p],
            "top_import": [[b, cname.get(b, ""), round(x)] for b, x in top_i],
            "permit_year": {"x": yr_range, "허가": [permit_year_kind[y].get("허가", 0) for y in yr_range],
                            "신고": [permit_year_kind[y].get("신고", 0) for y in yr_range],
                            "cancel": [cancel_year.get(y, 0) for y in yr_range]},
            "spc": spc.most_common(), "atc": [[k, ATC1.get(k, "미상"), n] for k, n in atc.most_common()],
            "ptype": ptype.most_common(15), "latest_year": latest_year,
            "status": Counter(row[6] for row in drugs).most_common(),
        }
        regulation = {
            "gmp": gmps, "gmp_kind": Counter(r[2] or "미상" for r in gmps).most_common(),
            "gmp_valid_year": sorted(Counter(r[5][:4] for r in gmps if r[5]).items()),
            "overseas_country": Counter(r[3] or "미상" for r in overseas).most_common(),
            "overseas_total": len(overseas), "overseas_companies": len({r[1] for r in overseas if r[1]}),
            "admins": admins, "admin_year": sorted(Counter(r[0][:4] for r in admins if r[0]).items()),
            "admin_type": Counter(r[8] for r in admins).most_common(),
        }
        supply = {
            "recalls": recalls, "suspends": suspends, "shortages": shortages, "letters": letters,
            "trend": {"recalls": monthly(recalls, 0), "suspends": monthly(suspends, 0),
                      "shortages": monthly(shortages, 0), "letters": monthly(letters, 0)},
            "shortage_status": Counter(r[7] or "미상" for r in shortages).most_common(),
            "suspend_status": Counter(r[8] or "미상" for r in suspends).most_common(),
        }

        self.write("meta.json", meta)
        self.write("dashboard.json", dashboard)
        self.write("drugs_index.json", {"cols": ["seq", "name", "entp", "bizrno", "permit", "spc", "status", "ingr_kr",
                                                 "ingr_en", "atc", "flags", "kind", "cancel"], "rows": drugs})
        self.write("companies_index.json", {"cols": ["bizrno", "name", "region", "items_active", "items_total",
                                                     "prod_latest", "import_latest", "gmp", "overseas", "admin",
                                                     "recall", "suspend", "shortage", "induty"],
                                            "latest_year": latest_year, "rows": companies})
        self.write("stats.json", stats)
        self.write("regulation.json", regulation)
        self.write("overseas.json", {"cols": ["company", "bizrno", "mftr", "country", "addr", "no"], "rows": overseas})
        self.write("supply.json", supply)
        self.write("changes.json", {"rows": changes, "baseline": baseline})
        for sh, d in drug_detail.items():
            self.write(f"drugs/{sh}.json", d)
        for sh, d in company_detail.items():
            self.write(f"companies/{sh}.json", d)
        return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/mfds.sqlite")
    ap.add_argument("--out", default="site/data")
    ap.add_argument("--summary")
    args = ap.parse_args()
    ex = Exporter(args.db, args.out)
    meta = ex.run()
    total = sum(ex.files.values())
    big = sorted(ex.files.items(), key=lambda x: -x[1])[:8]
    lines = [f"## 화면용 데이터 생성 (기준일 {meta['as_of']})", "",
             f"- 파일 {len(ex.files)}개, 합계 {total / 1e6:.1f}MB",
             "", "| 파일 | KB |", "|---|---|"] + [f"| {k} | {n / 1024:.0f} |" for k, n in big]
    text = "\n".join(lines) + "\n"
    print(text)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
