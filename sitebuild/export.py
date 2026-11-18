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


def ingr_parts(raw):
    """주성분 문자열을 성분 목록으로: 코드 제거, '|'·'/'로 나눔, 중복 제거, 정렬 (조합 순서가 달라도 같은 묶음)."""
    s = re.sub(r"\[[^\]]*\]", "", raw or "")
    return sorted({p.strip(" ,") for p in re.split(r"[|/]", s) if p.strip(" ,")})


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

    def rows_all(self, api_id):
        """API에서 더 이상 나오지 않는 행(is_present=0)까지 포함: (레코드, 현재 제공 여부, 마지막 확인 시각)."""
        return [(json.loads(p), bool(pr), ls) for p, pr, ls in self.con.execute(
            "SELECT payload, is_present, last_seen_at FROM raw_record WHERE api_id=? ORDER BY record_key", (api_id,))]

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

        # API에서 빠진 행(is_present=0)도 지우지 않고 화면에 계속 싣는다 (사용자 결정 2026-11-18, 전체 데이터).
        # 각 레코드에 __gone("1"=API에서 더 이상 조회 안 됨)·__last(마지막 확인 시각)를 붙여 상태를 표시한다.
        P, present_count = {}, {}
        for a in SOURCE:
            recs = []
            for r, pr, ls in self.rows_all(a):
                r["__gone"] = "" if pr else "1"
                r["__last"] = ls or ""
                recs.append(r)
            P[a] = recs
            present_count[a] = sum(1 for r in recs if not r["__gone"])
        ST = lambda r: "공개 종료" if r.get("__gone") else "공개 중"
        LS = lambda r: (r.get("__last") or "")[:10] if r.get("__gone") else ""
        detail = {v(r, "ITEM_SEQ"): r for r in P["drug_permit_detail"]}
        S = lambda r: v(r, "ITEM_SEQ")

        # ---------- 품목 ----------
        drugs = []
        drug_detail = defaultdict(dict)
        items_by_biz = defaultdict(list)
        ingr_map = {}  # 품목 -> 정렬된 성분 목록 (성분·시장 집계용)
        for r in P["drug_permit"]:
            seq = S(r)
            d = detail.get(seq, {})
            status = v(r, "CANCEL_NAME") or "정상"
            spc = "전문" if v(r, "SPCLTY_PBLC").startswith("전문") else ("일반" if v(r, "SPCLTY_PBLC") else "")
            atc = v(d, "ATC_CODE")
            flags = ("N" if v(d, "NEWDRUG_CLASS_NAME") == "신약" else "") + ("R" if v(d, "RARE_DRUG_YN") == "Y" else "") + ("G" if r.get("__gone") else "")  # G = API에서 더 이상 조회 안 됨
            ingr_kr = cut(strip_codes(v(d, "MAIN_ITEM_INGR")), 60)
            ingr_map[seq] = ingr_parts(v(d, "MAIN_ITEM_INGR")) or ingr_parts(v(r, "ITEM_INGR_NAME"))
            row = [seq, v(r, "ITEM_NAME"), v(r, "ENTP_NAME"), biz(v(r, "BIZRNO")), ymd(v(r, "ITEM_PERMIT_DATE")),
                   spc, status, ingr_kr, cut(v(r, "ITEM_INGR_NAME"), 60), atc, flags, v(r, "PERMIT_KIND_CODE"),
                   ymd(v(r, "CANCEL_DATE"))]
            drugs.append(row)
            items_by_biz[row[3]].append([seq, row[1], row[4], spc, status])
            drug_detail[shard(seq)][seq] = {
                "row": row,  # 상세 화면이 큰 목록 파일 없이 열리도록 기본 정보를 함께 둔다
                "eng": v(r, "ITEM_ENG_NAME"), "permit_no": v(r, "PRDUCT_PRMISN_NO"), "induty": v(r, "INDUTY"),
                "type": v(r, "PRDUCT_TYPE"), "edi": v(r, "EDI_CODE"), "cnsgn": v(d, "CNSGN_MANUF"),
                "narcotic": v(d, "NARCOTIC_KIND_CODE"), "chart": cut(v(d, "CHART"), 300),
                "storage": v(d, "STORAGE_METHOD"), "valid": v(d, "VALID_TERM"), "pack": cut(v(d, "PACK_UNIT"), 200),
                "material": cut(v(d, "MATERIAL_NAME"), 4000),  # 화면에서 성분 표로 풀어 보여 주므로 넉넉히
                "change_date": ymd(v(d, "CHANGE_DATE")),
                "change_hist": cut(v(d, "GBN_NAME"), 4000), "reexam": v(d, "REEXAM_TARGET"),
                "reexam_date": v(d, "REEXAM_DATE"), "ingr_eng": v(d, "MAIN_INGR_ENG"),
                "doc_ee": v(d, "EE_DOC_ID"), "doc_ud": v(d, "UD_DOC_ID"), "doc_nb": v(d, "NB_DOC_ID"),
                "protect_end": ymd(v(d, "DATA_PROTECT_END_DATE")),
                "has_detail": bool(d),
            }

        # ---------- 관련 이력 (품목·업체 연결) ----------
        rel = defaultdict(lambda: defaultdict(list))  # seq -> kind -> rows
        by_biz = defaultdict(lambda: defaultdict(list))

        # 회수도 API가 최근 몇 년치만 준다(2023-11-20부터). 행정처분과 같이 빠진 기록도 지우지 않고 계속 표시 (사용자 결정 2026-11-18)
        recalls = []
        for r, present, last_seen in self.rows_all("recall_drug"):
            row = [ymd(v(r, "RECALL_COMMAND_DATE")) or ymd(v(r, "RTRVL_CMMND_DT")), v(r, "PRDUCT"), v(r, "ENTRPS"),
                   biz(v(r, "BIZRNO")), S(r), cut(v(r, "RTRVL_RESN"), 200), v(r, "ENFRC_YN"),
                   "공개 중" if present else "공개 종료",          # [7]
                   "" if present else (last_seen or "")[:10]]     # [8] 마지막 확인일
            recalls.append(row)
        recalls.sort(key=lambda x: x[0], reverse=True)
        for row in recalls:
            if row[4]:
                rel[row[4]]["recall"].append([row[0], row[5], row[6], row[7]])
            if row[3]:
                by_biz[row[3]]["recall"].append([row[0], row[1], row[4], row[5], row[6], row[7]])

        suspends = []
        hidden_suspend = 0
        for r in P["supply_suspend"]:
            if v(r, "OPEN_AGREE_YN_NM") == "동의하지않음":
                hidden_suspend += 1
                continue
            row = [ymd(v(r, "REPORT_DATE")), v(r, "ITEM_NAME"), v(r, "ENTP_NAME"), biz(v(r, "BIZRNO")), S(r),
                   v(r, "SUSPEND_REPORT_FLAG"), ymd(v(r, "SUSPEND_DATE")), cut(v(r, "SUSPEND_REASON"), 200),
                   v(r, "REPORT_PGS_CODE"), v(r, "INV_QTY"), ST(r), LS(r)]  # [10] 공개 상태 [11] 마지막 확인일
            suspends.append(row)
        suspends.sort(key=lambda x: x[0], reverse=True)
        for row in suspends:
            if row[4]:
                rel[row[4]]["suspend"].append([row[0], row[5], row[6], row[7], row[8], row[10]])
            if row[3]:
                by_biz[row[3]]["suspend"].append([row[0], row[1], row[4], row[5], row[6], row[8], row[10]])

        shortages = []
        for r in P["supply_shortage"]:
            row = [ymd(v(r, "REPORT_DATE")), v(r, "ITEM_NAME"), v(r, "ENTP_NAME"), biz(v(r, "BIZRNO")), S(r),
                   cut(v(r, "SHORT_SUPPLY_REASON"), 200), ymd(v(r, "SUPPLY_PLAN_DATE")), v(r, "REPORT_PGS_CODE"),
                   cut(v(r, "TREATMENT_INFU"), 200), ST(r), LS(r)]  # [9] 공개 상태 [10] 마지막 확인일
            shortages.append(row)
        shortages.sort(key=lambda x: x[0], reverse=True)
        for row in shortages:
            if row[4]:
                rel[row[4]]["shortage"].append([row[0], row[5], row[6], row[7], row[9]])
            if row[3]:
                by_biz[row[3]]["shortage"].append([row[0], row[1], row[4], row[5], row[7], row[9]])

        # 행정처분은 공개 기간이 끝나면 API에서 빠진다. 사용자 결정(2026-11-18): 지우지 않고 계속 표시한다.
        # 수집 DB는 원래 삭제하지 않고 is_present=0으로만 표시하므로, 여기서 그 행까지 포함하고 상태를 붙인다.
        admins = []
        for r, present, last_seen in self.rows_all("admin_action"):
            disp = v(r, "ADM_DISPS_NAME")
            row = [ymd(v(r, "LAST_SETTLE_DATE")), v(r, "ENTP_NAME"), biz(v(r, "BIZRNO")), cut(v(r, "ITEM_NAME"), 120),
                   v(r, "ITEM_SEQ"), cut(disp, 240), cut(v(r, "BEF_APPLY_LAW"), 200), ymd(v(r, "RLS_END_DATE")),
                   admin_type(disp), v(r, "ADDR"),
                   "공개 중" if present else "공개 종료",          # [10] API 제공 여부
                   "" if present else (last_seen or "")[:10]]     # [11] 마지막으로 API에서 확인된 날 (UTC 날짜)
            admins.append(row)
        admins.sort(key=lambda x: x[0], reverse=True)
        admins_gone = sum(1 for r in admins if r[10] == "공개 종료")
        for row in admins:
            for seq in [s for s in re.split(r"[,\s]+", row[4]) if s]:
                rel[seq]["admin"].append([row[0], row[8], row[5], row[10]])
            if row[2]:
                by_biz[row[2]]["admin"].append([row[0], row[3], row[8], row[5], row[7], row[10]])

        letters = []
        for r in P["safety_letter"]:
            letters.append([ymd(v(r, "PBANC_YMD")), v(r, "TITLE"), v(r, "CHRG_DEP"), v(r, "ATTACH_FILE_URL"),
                            cut(v(r, "PBANC_CONT"), 300), v(r, "SAFT_LETT_NO"), ST(r), LS(r)])
        letters.sort(key=lambda x: x[0], reverse=True)

        # 생산·수입 (생산=백만원, 수입=달러)
        # 같은 품목·연도·구분이라도 보고 주체(업 일련번호 ENTP_SEQ·사업자번호)가 다르면 별개 행이다
        # (2026-11-18 점검: 1,535묶음 중 업번호·업체가 다른 경우가 대부분, 금액까지 같은 것은 43묶음).
        prod_item = defaultdict(dict)   # seq -> year -> [[part, amt, 업체명, 사업자번호, 업일련번호], ...]
        prod_biz = defaultdict(lambda: defaultdict(lambda: {"p": 0.0, "i": 0.0, "np": 0, "ni": 0}))
        prod_site = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"p": 0.0, "i": 0.0})))  # biz -> 업번호 -> year
        site_name = defaultdict(Counter)
        prod_year = defaultdict(lambda: {"p": 0.0, "i": 0.0, "np": 0, "ni": 0})
        names_from_prod = defaultdict(Counter)
        same_amt = defaultdict(list)    # (seq, year, part) -> [amt...] (같은 금액 중복 가능성 집계용)
        for r in P["production_import"]:
            year, part, amt = v(r, "DATE_YEAR"), v(r, "RESULT_PART"), num(v(r, "AMT"))
            if not year or amt is None or part not in ("생산", "수입"):
                continue
            k, n = ("p", "np") if part == "생산" else ("i", "ni")
            b = biz(v(r, "BIZRNO"))
            es = v(r, "ENTP_SEQ")
            prod_year[year][k] += amt
            prod_year[year][n] += 1
            if b:
                prod_biz[b][year][k] += amt
                prod_biz[b][year][n] += 1
                names_from_prod[b][v(r, "ENTP_NAME")] += 1
                if es:
                    prod_site[b][es][year][k] += amt
                    site_name[(b, es)][v(r, "ENTP_NAME")] += 1
            prod_item[S(r)].setdefault(year, []).append([part, round(amt, 3), v(r, "ENTP_NAME"), b, es])
            same_amt[(S(r), year, part)].append(round(amt, 3))
        dup_same = [(key, a[0]) for key, a in same_amt.items() if len(a) > 1 and len(set(a)) == 1 and a[0] > 0]
        prod_dup = {"groups": len(dup_same),
                    "p": round(sum(x for (s_, y_, pt), x in dup_same if pt == "생산"), 1),
                    "i": round(sum(x for (s_, y_, pt), x in dup_same if pt == "수입"))}

        gmps = []
        for r in P["gmp"]:
            gmps.append([v(r, "BSSH_NM"), biz(v(r, "BIZRNO")), v(r, "KGMP_BGMP_NAME"), v(r, "GMP_INGR_MM_GROUP_NAME"),
                         v(r, "FCTR_ADDR"), ymd(v(r, "VLD_PRD_YMD")), ST(r)])
        gmps.sort(key=lambda x: x[5], reverse=True)
        overseas = []
        for r in P["overseas_mfr"]:
            overseas.append([v(r, "BSSH_NM"), biz(v(r, "BIZRNO")), v(r, "MFTR_NM"), v(r, "NATN_CD_NM"),
                             cut(v(r, "MFTR_ADDR"), 120), v(r, "MFTR_PRMSN_NO"), ST(r),
                             num(v(r, "MFTR_LATD")), num(v(r, "MFTR_LGTD"))])  # [7][8] 좌표 (지도용)
        for row in gmps:
            if row[1]:
                by_biz[row[1]]["gmp"].append([row[2], row[3], row[4], row[5], row[6]])
        for row in overseas:
            if row[1]:
                by_biz[row[1]]["overseas"].append([row[2], row[3], row[5], row[6]])

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
        # 소재지: 업체허가 목록은 허가(업종)마다 행이 따로 있고 행마다 주소(시·군·구)가 다를 수 있다 → 전부 보관
        regions = defaultdict(list)
        region_fallback = {}
        for r in P["company_list"]:
            b = biz(v(r, "BIZRNO"))
            if not b:
                continue
            addr = v(r, "ADRES")
            lic[b].append([v(r, "INDUTY"), ymd(v(r, "PRMISN_DT")), v(r, "PRMISN_NO"), addr, ST(r)])
            lic_names[b][v(r, "ENTRPS")] += 1  # 대표 상호는 업체허가 목록을 우선
            if addr and addr not in regions[b]:
                regions[b].append(addr)
        # GMP 적합판정 공장 소재지 (업체허가 목록과 별개 출처)
        factories = defaultdict(list)
        for row in gmps:
            if row[1] and row[4]:
                short = " ".join(row[4].split()[:2])
                if short not in factories[row[1]]:
                    factories[row[1]].append(short)
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
                region_fallback.setdefault(row[2], row[9])
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
            regs = regions.get(b) or ([region_fallback[b]] if region_fallback.get(b) else [])
            facs = factories.get(b, [])
            reg_text = regs[0] + (f" 외 {len(regs) - 1}곳" if len(regs) > 1 else "") if regs else ""
            companies.append([b, nm, reg_text, active, len(items), round(ly.get("p", 0), 1) if ly else None,
                              round(ly.get("i", 0)) if ly else None, len(bz.get("gmp", [])),
                              len(bz.get("overseas", [])), len(bz.get("admin", [])), len(bz.get("recall", [])),
                              len(bz.get("suspend", [])), len(bz.get("shortage", [])), "·".join(induty),
                              " · ".join(facs)])
            company_detail[shard(b)][b] = {
                "name": nm, "names": [n for n, _ in names[b].most_common(5)], "region": reg_text,
                "regions": regs, "region_from_admin": not regions.get(b) and bool(regs), "factories": facs,
                "licenses": lic.get(b, []), "items": items,
                "prod": {y: {k: round(x, 3) if isinstance(x, float) else x for k, x in d.items()}
                         for y, d in sorted(py.items())},
                **{k: bz.get(k, [])[:300] for k in ("gmp", "admin", "recall", "suspend", "shortage")},
                "overseas": bz.get("overseas", [])[:300], "overseas_total": len(bz.get("overseas", [])),
                # 업 일련번호(허가별)마다 생산·수입. 2개 이상일 때만 의미가 있다
                "prod_sites": {es: {"name": site_name[(b, es)].most_common(1)[0][0] if site_name[(b, es)] else "",
                                    "years": {y: {"p": round(d["p"], 3), "i": round(d["i"], 3)} for y, d in sorted(ys.items())}}
                               for es, ys in prod_site.get(b, {}).items()} if len(prod_site.get(b, {})) > 1 else {},
            }

        # ---------- 위탁제조 관계 (허가 상세 CNSGN_MANUF: 수탁 제조업체 '이름'만 있음) ----------
        # 사업자번호가 없으므로 업체로 확정 연결하지 않는다. 수탁 쪽은 '상호가 정확히 같은 경우'만 참고로 보여 준다.
        norm = lambda s: re.sub(r"\s+", "", s or "")
        cn_by_name = defaultdict(list)
        for sh in drug_detail.values():
            for seq, d in sh.items():
                cn = d.get("cnsgn", "")
                r0 = d["row"]
                if not cn:
                    continue
                for part in [x.strip() for x in re.split(r"[,/]", cn) if x.strip()]:
                    cn_by_name[norm(part)].append([seq, r0[1], r0[2], r0[3], r0[6]])
                if r0[3] in company_detail[shard(r0[3])]:
                    company_detail[shard(r0[3])][r0[3]].setdefault("outsourced", []).append([seq, r0[1], cn, r0[6]])
        for sh, comps in company_detail.items():
            for b, c in comps.items():
                inbound, seen = [], set()
                for n in c["names"]:
                    for x in cn_by_name.get(norm(n), []):
                        if x[0] not in seen and x[3] != b:
                            seen.add(x[0])
                            inbound.append(x)
                c["contracted_in"] = inbound[:300]
                c["contracted_in_total"] = len(inbound)
                c["outsourced"] = c.get("outsourced", [])[:300]

        # ---------- 성분·ATC 시장·품목 순위·독점 종료 예정 ----------
        item_amt = defaultdict(lambda: defaultdict(lambda: {"p": 0.0, "i": 0.0}))
        for seq, ys in prod_item.items():
            for y, lst in ys.items():
                for x in lst:
                    item_amt[seq][y]["p" if x[0] == "생산" else "i"] += x[1]
        prev_year = years[-2] if len(years) > 1 else ""
        amt = lambda seq, y, k: item_amt[seq][y][k] if seq in item_amt and y in item_amt[seq] else 0.0

        def market(keysf, with_seqs=False):
            agg = {}
            for r in drugs:
              for k in keysf(r):
                a = agg.setdefault(k, {"n": 0, "act": 0, "cos": set(), "p": 0.0, "i": 0.0, "bp": Counter(), "seqs": []})
                a["seqs"].append(r[0])
                a["n"] += 1
                if r[6] == "정상" and "G" not in r[10]:
                    a["act"] += 1
                if r[3]:
                    a["cos"].add(r[3])
                p, i = amt(r[0], latest_year, "p"), amt(r[0], latest_year, "i")
                a["p"] += p
                a["i"] += i
                if r[3] and p:
                    a["bp"][r[3]] += p
            return [[k, a["n"], a["act"], len(a["cos"]), round(a["p"], 1), round(a["i"]),
                     [[b, cname_all.get(b, ""), round(x, 1)] for b, x in a["bp"].most_common(3)]]
                    + ([a["seqs"]] if with_seqs else [])
                    for k, a in sorted(agg.items(), key=lambda kv: -kv[1]["n"])]

        cname_all = {c[0]: c[1] for c in companies}
        # 성분 조합별(정렬된 조합이 같으면 같은 묶음)과 개별 성분별(복합제에 들어간 것까지 포함) 두 가지
        ingredients = market(lambda r: [" + ".join(ingr_map[r[0]])] if ingr_map.get(r[0]) else [], with_seqs=True)
        ingredients_single = market(lambda r: ingr_map.get(r[0], []), with_seqs=True)
        atc_market = market(lambda r: [r[9][:4] if len(r[9]) >= 4 else r[9]] if r[9] else [])

        def top_items(k, n=50):
            rows = [(r, amt(r[0], latest_year, k), amt(r[0], prev_year, k)) for r in drugs if amt(r[0], latest_year, k) > 0]
            rows.sort(key=lambda x: -x[1])
            return [[r[0], r[1], r[2], r[3], round(a, 1), round(b, 1)] for r, a, b in rows[:n]]

        def growth(k, up=True, n=30, base=1000.0):
            # 기준 금액이 너무 작은 품목은 증감률이 왜곡되므로 전년 base(백만원) 이상만
            rows = []
            for r in drugs:
                a, b = amt(r[0], latest_year, k), amt(r[0], prev_year, k)
                if b >= base:
                    rows.append((r, a, b, (a - b) / b * 100))
            rows.sort(key=lambda x: -x[3] if up else x[3])
            return [[r[0], r[1], r[2], r[3], round(a, 1), round(b, 1), round(g, 1)] for r, a, b, g in rows[:n]]

        horizon = (as_of_dt - timedelta(days=365)).strftime("%Y-%m-%d")
        exclusivity = []
        for sh in drug_detail.values():
            for seq, d in sh.items():
                r0 = d["row"]
                ends = []
                m = re.findall(r"\d{4}-\d{2}-\d{2}", d.get("reexam_date", ""))
                if m:
                    ends.append(("재심사", m[-1], d.get("reexam", "")))
                if d.get("protect_end"):
                    ends.append(("자료보호", d["protect_end"], ""))
                for kind, end, note in ends:
                    if end >= horizon:
                        exclusivity.append([seq, r0[1], r0[2], r0[3], kind, end, r0[7] or r0[8], note, r0[6]])
        exclusivity.sort(key=lambda x: x[5])

        markets = {"latest": latest_year, "prev": prev_year, "ingredients": ingredients, "ingredients_single": ingredients_single, "atc": atc_market,
                   "atc1": ATC1, "top_p": top_items("p"), "top_i": top_items("i"),
                   "grow_up": growth("p", True), "grow_down": growth("p", False), "exclusivity": exclusivity}

        # ---------- 통계 ----------
        permit_year = Counter(row[4][:4] for row in drugs if row[4])
        permit_year_kind = defaultdict(Counter)
        for row in drugs:
            if row[4]:
                permit_year_kind[row[4][:4]][row[11] or "기타"] += 1
        cancel_year = Counter(row[12][:4] for row in drugs if row[12])
        active_rows = [row for row in drugs if row[6] == "정상" and "G" not in row[10]]  # API에서 빠진 품목은 유효로 세지 않음
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
            api_meta.append({"id": a, "name": name, "count": present_count[a], "kept": len(P[a]), "last": lastok, "baseline": baseline.get(a),
                             "url": f"https://www.data.go.kr/data/{did}/openapi.do"})

        def span(rows, idx):
            ds = sorted(r[idx] for r in rows if r[idx])
            return [ds[0], ds[-1]] if ds else None

        # API가 제공하는 기간 (예: 회수는 최근 몇 년치만 제공) — 화면에 "이 기간 자료만 있음"을 알리기 위함
        coverage = {"recall_drug": span(recalls, 0), "admin_action": span(admins, 0),
                    "supply_suspend": span(suspends, 0), "supply_shortage": span(shortages, 0),
                    "safety_letter": span(letters, 0), "drug_permit": span(drugs, 4),
                    "production_import": [years[0], years[-1]] if years else None}
        meta = {"as_of": self.as_of, "since30": self.since30, "coverage": coverage, "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
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
                "recalls_total": len(recalls), "recalls_gone": sum(1 for r in recalls if r[7] == "공개 종료"), "admins_total": len(admins), "admins_gone": admins_gone, "suspends_total": len(suspends), "suspends_gone": sum(1 for r in suspends if r[10] == "공개 종료"),
                "shortages_total": len(shortages), "shortages_gone": sum(1 for r in shortages if r[9] == "공개 종료"), "items_gone": sum(1 for r in drugs if "G" in r[10]), "gmp_total": len(gmps), "overseas_total": len(overseas),
                "letters_total": len(letters),
            },
            "new_permits": [[r[0], r[1], r[2], r[3], r[4], r[5], r[11]] for r in new_permits[:15]],
            "new_cancels": [[r[0], r[1], r[2], r[3], r[12], r[6]] for r in new_cancels[:15]],
            "recalls": recalls[:8], "admins": [[r[0], r[1], r[2], r[3], r[8], r[10]] for r in admins[:8]],
            "suspends": [[r[0], r[1], r[2], r[3], r[4], r[5], r[10]] for r in suspends[:8]],
            "shortages": [[r[0], r[1], r[2], r[3], r[4], r[7], r[9]] for r in shortages[:8]],
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
            "ptype": ptype.most_common(15), "latest_year": latest_year, "prod_dup": prod_dup,
            "status": Counter(row[6] for row in drugs).most_common(),
        }
        regulation = {
            "gmp": gmps, "gmp_kind": Counter(r[2] or "미상" for r in gmps).most_common(),
            "gmp_valid_year": sorted(Counter(r[5][:4] for r in gmps if r[5]).items()),
            "overseas_country": Counter(r[3] or "미상" for r in overseas).most_common(),
            "overseas_total": len(overseas), "overseas_companies": len({r[1] for r in overseas if r[1]}),
            "admins": admins, "admin_year": sorted(Counter(r[0][:4] for r in admins if r[0]).items()),
            "admin_type": Counter(r[8] for r in admins).most_common(), "admin_gone": admins_gone,
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
                                                     "recall", "suspend", "shortage", "induty", "factories"],
                                            "latest_year": latest_year, "rows": companies})
        self.write("stats.json", stats)
        self.write("regulation.json", regulation)
        self.write("overseas.json", {"cols": ["company", "bizrno", "mftr", "country", "addr", "no"], "rows": overseas})
        self.write("supply.json", supply)
        self.write("markets.json", markets)
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
