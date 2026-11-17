"""수집 대상 API 등록부.

모든 경로는 2026-11-17 실제 호출로 검증된 것만 등록한다 (docs/API_CATALOG.md E절).

필드:
  id       내부 식별자 (DB의 api_id)
  name     표시 이름
  data_id  공공데이터포털 데이터 ID (https://www.data.go.kr/data/{data_id}/openapi.do)
  path     기본 URL(https://apis.data.go.kr/1471000/) 뒤의 서비스/오퍼레이션 경로
  key      레코드 식별 필드 목록. None이면 레코드 전체 해시를 식별자로 쓴다
           (이 경우 값이 바뀌면 '수정'이 아니라 '삭제+추가'로 기록된다).
           같은 실행 안에서 키가 겹치면 해시를 덧붙여 구분한다 (store.py).
  tier     core     : 정기 수집 기본 대상
           heavy    : 건수·용량이 커서 별도 실행 (예: DUR 병용금기 79만 건)
           optional : 범위 결정 전 (화장품)
"""

APIS = [
    # --- 필수 (사용자 선정, 승인·검증 완료) ---
    {"id": "drug_permit", "name": "의약품 제품 허가 목록", "data_id": "15095677",
     "path": "DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnInq08", "key": ["ITEM_SEQ"], "tier": "core"},
    {"id": "drug_permit_detail", "name": "의약품 제품 허가 상세", "data_id": "15095677",
     "path": "DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnDtlInq08", "key": ["ITEM_SEQ"], "tier": "heavy"},
    {"id": "drug_ingredient", "name": "의약품 제품 주성분 상세", "data_id": "15095677",
     "path": "DrugPrdtPrmsnInfoService08/getDrugPrdtMcpnDtlInq08", "key": None, "tier": "heavy"},
    {"id": "company_list", "name": "의약품 등 업체허가 목록", "data_id": "15095682",
     "path": "DrugEtcBsshBspmStusService01/getDrugBsshListInq01", "key": None, "tier": "core"},
    {"id": "company_detail", "name": "의약품 등 업체허가 상세(공장)", "data_id": "15095682",
     "path": "DrugEtcBsshBspmStusService01/getDrugBsshItemInq01", "key": None, "tier": "core"},
    {"id": "production_import", "name": "의약품 생산·수입실적", "data_id": "15056880",
     "path": "MdcinPrdctnImportAcmsltService02/getMdcinPrdctnImportrstList02",
     "key": ["ITEM_SEQ", "DATE_YEAR", "RESULT_PART"], "tier": "core"},
    {"id": "admin_action", "name": "의약품 행정처분", "data_id": "15058457",
     "path": "MdcinExaathrService04/getMdcinExaathrList04", "key": ["ADM_DISPS_SEQ"], "tier": "core"},
    {"id": "recall_drug", "name": "의약품 회수·판매중지", "data_id": "15059114",
     "path": "MdcinRtrvlSleStpgeInfoService05/getMdcinRtrvlSleStpgelList05",
     "key": ["ITEM_SEQ", "RTRVL_CMMND_DT"], "tier": "core"},
    {"id": "recall_etc", "name": "의약품외 회수·판매중지", "data_id": "15059114",
     "path": "MdcinRtrvlSleStpgeInfoService05/getMdcinRtrvlSleStpgelEtcList05", "key": None, "tier": "core"},
    {"id": "supply_suspend", "name": "의약품 생산·수입·공급중단", "data_id": "15057899",
     "path": "MdcinPrdctnIncmeSuplyService2/getMdcinPrdctnIncmeSuplyList",
     "key": ["SUSPEND_REPORT_SEQ"], "tier": "core"},
    {"id": "gmp", "name": "의약품 GMP 적합판정서 발급현황", "data_id": "15097207",
     "path": "DrugGmpStbltJgmtIssuStusService/getDrugGmpStbltJgmtIssuStusInq", "key": None, "tier": "core"},
    {"id": "overseas_mfr", "name": "의약품 해외제조소", "data_id": "15090422",
     "path": "OvseaMnfctrService/getOvseaMnfctrInq", "key": None, "tier": "core"},
    {"id": "quasi_drug", "name": "의약외품 제품 허가", "data_id": "15095679",
     "path": "QdrgPrdtPrmsnInfoService03/getQdrgPrdtPrmsnInfoInq03", "key": ["ITEM_SEQ"], "tier": "core"},
    {"id": "cosmetics_mfr", "name": "화장품 제조(판매)업", "data_id": "15020628",
     "path": "CsmtcsMfcrtrInfoService02/getCsmtcsMfcrtrInfoList02", "key": None, "tier": "optional"},

    # --- 권장 (2026-11-17 승인·검증) ---
    {"id": "supply_shortage", "name": "의약품 공급부족", "data_id": "15056886",
     "path": "MdcinSuplyLackService03/getMdcinSuplyLackList01",
     "key": ["SHORT_SUPPLY_REPORT_SEQ"], "tier": "core"},
    {"id": "safety_letter", "name": "의약품 안전성서한", "data_id": "15059182",
     "path": "DrugSafeLetterService02/getDrugSafeLetterList02", "key": ["SAFT_LETT_NO"], "tier": "core"},
    {"id": "reexam", "name": "의약품 재심사", "data_id": "15058034",
     "path": "MdcinRejdgeService02/getMdcinRdjdgeList02", "key": None, "tier": "heavy"},
    {"id": "reeval", "name": "의약품 재평가", "data_id": "15057382",
     "path": "MdcinRevalService03/getMdcinRevalList03", "key": None, "tier": "core"},
    {"id": "rare_drug", "name": "희귀의약품", "data_id": "15057935",
     "path": "RareMdcinInfoService02/getRareMdcinList02", "key": None, "tier": "core"},
    {"id": "patent", "name": "의약품 특허정보", "data_id": "15057623",
     "path": "MdcinPatentInfoService2/getMdcinPatentInfoList2", "key": None, "tier": "heavy"},
    {"id": "patent_domestic", "name": "의약품 국내 특허현황", "data_id": "15117409",
     "path": "DrugDmstPtntStusService/getDrugDmstPtntStusService", "key": None, "tier": "core"},
    {"id": "priority_sale", "name": "우선판매품목허가 의약품", "data_id": "15097204",
     "path": "PrtySalePrdlstPrmsnDrugService/getPrtySalePrdlstPrmsnDrugInq", "key": None, "tier": "core"},
    {"id": "bioequivalence", "name": "생동성인정품목", "data_id": "15058447",
     "path": "MdcBioEqInfoService01/getMdcBioEqList01", "key": ["ITEM_SEQ"], "tier": "core"},
    {"id": "dmf", "name": "원료의약품등록(DMF)", "data_id": "15057075",
     "path": "MdcDmfInfoService02/getMdcDmfList02", "key": ["DMF_PERMIT_NO"], "tier": "core"},
    {"id": "clinical_trial", "name": "의약품 임상시험 정보", "data_id": "15056835",
     "path": "MdcinClincTestInfoService02/getMdcinClincTestInfoList02", "key": ["CLNC_TEST_SN"], "tier": "core"},
    {"id": "clinical_plan", "name": "의약품 임상시험 계획 상세", "data_id": "15090589",
     "path": "ClncExamPlanDtlService03/getClncExamPlanDtlInq03", "key": None, "tier": "core"},
    {"id": "drug_bundle", "name": "묶음의약품정보", "data_id": "15063908",
     "path": "DrbBundleInfoService02/getDrbBundleList02", "key": None, "tier": "core"},

    # --- DUR 품목정보 (15059486) ---
    {"id": "dur_item", "name": "DUR 품목정보", "data_id": "15059486",
     "path": "DURPrdlstInfoService03/getDurPrdlstInfoList03", "key": ["ITEM_SEQ"], "tier": "core"},
    {"id": "dur_combination", "name": "DUR 병용금기", "data_id": "15059486",
     "path": "DURPrdlstInfoService03/getUsjntTabooInfoList03", "key": None, "tier": "heavy"},
    {"id": "dur_elderly", "name": "DUR 노인주의", "data_id": "15059486",
     "path": "DURPrdlstInfoService03/getOdsnAtentInfoList03", "key": None, "tier": "core"},
    {"id": "dur_age", "name": "DUR 특정연령대금기", "data_id": "15059486",
     "path": "DURPrdlstInfoService03/getSpcifyAgrdeTabooInfoList03", "key": None, "tier": "core"},
    {"id": "dur_dose", "name": "DUR 용량주의", "data_id": "15059486",
     "path": "DURPrdlstInfoService03/getCpctyAtentInfoList03", "key": None, "tier": "core"},
    {"id": "dur_period", "name": "DUR 투여기간주의", "data_id": "15059486",
     "path": "DURPrdlstInfoService03/getMdctnPdAtentInfoList03", "key": None, "tier": "core"},
    {"id": "dur_duplicate", "name": "DUR 효능군중복", "data_id": "15059486",
     "path": "DURPrdlstInfoService03/getEfcyDplctInfoList03", "key": None, "tier": "core"},
    {"id": "dur_split", "name": "DUR 서방정분할주의", "data_id": "15059486",
     "path": "DURPrdlstInfoService03/getSeobangjeongPartitnAtentInfoList03", "key": None, "tier": "core"},
    {"id": "dur_pregnancy", "name": "DUR 임부금기", "data_id": "15059486",
     "path": "DURPrdlstInfoService03/getPwnmTabooInfoList03", "key": None, "tier": "core"},
]

TIERS = ("core", "heavy", "optional")


def select_apis(spec):
    """'all', 'tier:core', 'tier:core+heavy', 또는 'id1,id2' 형식으로 대상 API를 고른다."""
    spec = (spec or "").strip()
    if spec in ("", "all"):
        return list(APIS)
    if spec.startswith("tier:"):
        tiers = [t for t in spec[5:].split("+") if t]
        bad = [t for t in tiers if t not in TIERS]
        if bad:
            raise ValueError(f"알 수 없는 tier: {', '.join(bad)}")
        return [a for a in APIS if a["tier"] in tiers]
    ids = [s.strip() for s in spec.split(",") if s.strip()]
    by_id = {a["id"]: a for a in APIS}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        raise ValueError(f"알 수 없는 API id: {', '.join(unknown)}")
    return [by_id[i] for i in ids]
