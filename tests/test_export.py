import json
import os
import tempfile
import unittest

from collector import store as S
from collector.apis import APIS
from sitebuild import export as E


def put(con, run_id, api_id, rec, key):
    text = S.canonical(rec)
    con.execute("INSERT INTO raw_record(api_id, record_key, record_hash, payload, first_seen_run, last_seen_run,"
                " first_seen_at, last_seen_at, is_present) VALUES (?,?,?,?,?,?,?,?,1)",
                (api_id, key, S.record_hash(text), text, run_id, run_id, "2026-11-17T00:00:00Z", "2026-11-17T00:00:00Z"))


class HelperTests(unittest.TestCase):
    def test_ymd(self):
        self.assertEqual(E.ymd("20261117"), "2026-11-17")
        self.assertEqual(E.ymd("2026-11-17"), "2026-11-17")
        self.assertEqual(E.ymd("20261112000000"), "2026-11-12")
        self.assertEqual(E.ymd("None"), "")
        self.assertEqual(E.ymd("2026-1"), "")

    def test_v_and_biz(self):
        self.assertEqual(E.v({"A": "None"}, "A"), "")
        self.assertEqual(E.v({"A": " x "}, "A"), "x")
        self.assertEqual(E.biz("123-45-67890"), "1234567890")
        self.assertEqual(E.biz("None"), "")

    def test_admin_type(self):
        self.assertEqual(E.admin_type("제조업무정지 3개월"), "업무정지")
        self.assertEqual(E.admin_type("과징금 부과"), "과징금")
        self.assertEqual(E.admin_type("시정명령"), "기타")


class ExportTests(unittest.TestCase):
    def test_export_end_to_end(self):
        tmp = tempfile.mkdtemp()
        db = os.path.join(tmp, "t.sqlite")
        con = S.connect(db)
        S.register_apis(con, APIS)
        run_id = S.start_run(con, "test", "t")
        S.finish_run(con, run_id, "complete", 0)
        con.execute("UPDATE collect_run SET finished_at='2026-11-17T18:30:00Z'")
        put(con, run_id, "drug_permit", {"ITEM_SEQ": "202600001", "ITEM_NAME": "가정", "ENTP_NAME": "가제약(주)",
                                          "BIZRNO": "1234567890", "ITEM_PERMIT_DATE": "20261110",
                                          "SPCLTY_PBLC": "전문의약품", "CANCEL_NAME": "정상", "CANCEL_DATE": "None",
                                          "PERMIT_KIND_CODE": "허가", "ITEM_INGR_NAME": "Acetaminophen"}, "202600001")
        put(con, run_id, "drug_permit", {"ITEM_SEQ": "199900002", "ITEM_NAME": "나정", "ENTP_NAME": "가제약(주)",
                                          "BIZRNO": "1234567890", "ITEM_PERMIT_DATE": "19990101",
                                          "SPCLTY_PBLC": "일반의약품", "CANCEL_NAME": "취하", "CANCEL_DATE": "20261101",
                                          "PERMIT_KIND_CODE": "신고"}, "199900002")
        put(con, run_id, "drug_permit_detail", {"ITEM_SEQ": "202600001", "ATC_CODE": "N02BE01",
                                                 "NEWDRUG_CLASS_NAME": "신약", "RARE_DRUG_YN": "N",
                                                 "MAIN_ITEM_INGR": "[M1]아세트아미노펜", "PRDUCT_TYPE": "[01140]해열진통소염제",
                                                 "EE_DOC_ID": "https://nedrug.mfds.go.kr/x"}, "202600001")
        put(con, run_id, "company_list", {"BIZRNO": "1234567890", "ENTRPS": "가제약주식회사", "INDUTY": "의약품",
                                           "PRMISN_DT": "19800101", "ADRES": "충청북도 음성군", "PRMISN_NO": "1"}, "h:1")
        put(con, run_id, "company_list", {"BIZRNO": "1234567890", "ENTRPS": "가제약주식회사", "INDUTY": "의약외품",
                                           "PRMISN_DT": "19900101", "ADRES": "경기도 이천시", "PRMISN_NO": "2"}, "h:2")
        put(con, run_id, "production_import", {"ITEM_SEQ": "202600001", "DATE_YEAR": "2025", "RESULT_PART": "생산",
                                                "AMT": "100.5", "BIZRNO": "1234567890", "ENTP_NAME": "가제약(주)"}, "a")
        put(con, run_id, "production_import", {"ITEM_SEQ": "199900002", "DATE_YEAR": "2025", "RESULT_PART": "수입",
                                                "AMT": "2000", "BIZRNO": "1234567890", "ENTP_NAME": "가제약(주)"}, "b")
        put(con, run_id, "recall_drug", {"ITEM_SEQ": "202600001", "PRDUCT": "가정", "ENTRPS": "가제약(주)",
                                          "BIZRNO": "1234567890", "RECALL_COMMAND_DATE": "20261115",
                                          "RTRVL_RESN": "함량 부적합", "ENFRC_YN": "Y"}, "r1")
        put(con, run_id, "supply_suspend", {"ITEM_SEQ": "202600001", "ITEM_NAME": "가정", "ENTP_NAME": "가제약(주)",
                                             "BIZRNO": "1234567890", "REPORT_DATE": "20261112",
                                             "OPEN_AGREE_YN_NM": "동의함", "SUSPEND_REPORT_FLAG": "생산"}, "s1")
        put(con, run_id, "supply_suspend", {"ITEM_SEQ": "199900002", "ITEM_NAME": "나정", "BIZRNO": "1234567890",
                                             "REPORT_DATE": "20261112", "OPEN_AGREE_YN_NM": "동의하지않음"}, "s2")
        put(con, run_id, "admin_action", {"ADM_DISPS_SEQ": "1", "ENTP_NAME": "가제약(주)", "BIZRNO": "1234567890",
                                           "ITEM_SEQ": "202600001,199900002", "ADM_DISPS_NAME": "제조업무정지 1개월",
                                           "LAST_SETTLE_DATE": "20261020"}, "1")
        put(con, run_id, "gmp", {"BSSH_NM": "가제약(주)", "BIZRNO": "1234567890", "KGMP_BGMP_NAME": "완제의약품",
                                  "VLD_PRD_YMD": "2028-05-24", "FCTR_ADDR": "충청남도 당진시 합덕읍 1"}, "g")
        put(con, run_id, "gmp", {"BSSH_NM": "가제약(주)", "BIZRNO": "1234567890", "KGMP_BGMP_NAME": "원료의약품",
                                  "VLD_PRD_YMD": "2028-01-01", "FCTR_ADDR": "경기도 이천시 2"}, "g2")
        put(con, run_id, "safety_letter", {"TITLE": "서한", "PBANC_YMD": "2026-11-10", "SAFT_LETT_NO": "1"}, "l")
        con.commit()
        con.close()

        out = os.path.join(tmp, "out")
        meta = E.Exporter(db, out).run()
        self.assertEqual(meta["as_of"], "2026-11-18")  # UTC 18:30 → KST 다음날
        load = lambda p: json.load(open(os.path.join(out, p), encoding="utf-8"))
        dash = load("dashboard.json")
        self.assertEqual(dash["kpi"]["items_active"], 1)
        self.assertEqual(dash["kpi"]["new_permits_30"], 1)
        self.assertEqual(dash["kpi"]["new_cancels_30"], 1)
        self.assertEqual(dash["kpi"]["suspends_total"], 1)  # 공개 비동의 1건 제외
        self.assertEqual(meta["hidden_suspend"], 1)
        comp = load("companies_index.json")["rows"]
        self.assertEqual(len(comp), 1)
        self.assertEqual(comp[0][1], "가제약주식회사")  # 업체허가 목록 상호 우선
        self.assertEqual((comp[0][5], comp[0][6]), (100.5, 2000))  # 생산 백만원·수입 달러 따로
        self.assertEqual(comp[0][2], "충청북도 음성군 외 1곳")  # 허가별 주소를 모두 반영
        self.assertEqual(comp[0][14], "충청남도 당진시 · 경기도 이천시")  # GMP 공장 소재지
        det = load("companies/90.json")["1234567890"]
        self.assertEqual(det["regions"], ["충청북도 음성군", "경기도 이천시"])
        self.assertEqual(det["licenses"][1][3], "경기도 이천시")
        self.assertEqual(len(det["items"]), 2)
        self.assertEqual(det["prod"]["2025"]["p"], 100.5)
        drug = load("drugs/01.json")["202600001"]
        self.assertEqual(drug["rel"]["recall"][0][0], "2026-11-15")
        self.assertEqual(len(drug["rel"]["admin"]), 1)
        self.assertEqual(drug["doc_ee"], "https://nedrug.mfds.go.kr/x")
        self.assertEqual(drug["row"][:2], ["202600001", "가정"])
        idx = load("drugs_index.json")
        row = dict(zip(idx["cols"], idx["rows"][0] if idx["rows"][0][0] == "202600001" else idx["rows"][1]))
        self.assertEqual((row["atc"], row["flags"], row["ingr_kr"]), ("N02BE01", "N", "아세트아미노펜"))
        stats = load("stats.json")
        self.assertEqual(stats["prod_year"]["p"], [100.5])
        self.assertEqual(stats["prod_year"]["i"], [2000])


if __name__ == "__main__":
    unittest.main()
