# API 카탈로그 (MFDS INSIGHT)

조사일: 2026-11-17
1차 출처: 의약품안전나라 공공데이터 공개 목록 https://nedrug.mfds.go.kr/pbp/CCBGA01/getList (총 73건, 10건씩 8페이지, 전 페이지 순회 완료)
상세 출처: 공공데이터포털 상세 페이지 https://www.data.go.kr/data/{ID}/openapi.do

## 조사 상태 범례

| 상태 | 의미 |
|---|---|
| **공식문서확인** | 공공데이터포털 상세 페이지에서 명세 확인 (로그아웃 상태 열람) |
| **목록만확인** | 의약품안전나라 목록에만 있음. 상세 페이지 미조사 |
| **실제호출검증** | 사용자 계정 승인 후 실제 응답 확인 (이번 조사에서는 **미수행**) |
| **추가검증필요** | 공식 정보 간 불일치 또는 확인되지 않은 항목 있음 |

## 요약

- 목록 항목: 73건 / 고유 data.go.kr ID: **59건** (같은 ID에 여러 서비스가 묶인 경우가 있음)
- 상세 페이지 확인 완료: **59개 ID 전부** (A절 10개 + B절 49개). 폐지·삭제된 페이지 없음
- 실제 호출 검증: **A절 10개 ID 완료** (2026-11-17, 회수 상세 2종 제외 전 오퍼레이션, E-3절). A표의 "공식문서확인"은 모두 **실제호출검증**으로 갱신됨
- B절 49개 ID 중 권장 13개 실제호출검증 완료 (E-4절). 희귀의약품 1개는 승인됐으나 게이트웨이 미반영(403)으로 재시도 필요. 나머지 35개는 공식문서확인만
- 활용 승인: **24건** (A절 10 + 권장 14)

## A. 사용자 선정 9개 + 의약외품 (실제호출검증 완료 — 상태 열은 최초 조사 시점 기록)

| # | 서비스명 | data.go.kr ID | 기본 URL / 오퍼레이션 | 업데이트 주기(페이지 표기) | 활용신청 수(상세 메타) | 상태 |
|---|---|---|---|---|---|---|
| 4 | 의약품 행정처분 정보 | 15058457 | `https://apis.data.go.kr/1471000/MdcinExaathrService04` / `getMdcinExaathrList04` | 실시간 | 496 | 공식문서확인 |
| 7 | 의약품 제품 허가정보 | 15095677 | `https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08` / `getDrugPrdtPrmsnInq08`(목록), `getDrugPrdtPrmsnDtlInq08`(상세), `getDrugPrdtMcpnDtlInq08`(주성분 상세) | 실시간 | 10,145 | 공식문서확인 (**3개 목록 항목이 같은 ID 공유**) |
| 8 | 의약품 생산·수입실적현황 | 15056880 | `https://apis.data.go.kr/1471000/MdcinPrdctnImportAcmsltService02` / `getMdcinPrdctnImportrstList02` | **연간** | 1,071 | 공식문서확인 |
| 9 | 의약품 회수·판매중지 정보 | 15059114 | `https://apis.data.go.kr/1471000/MdcinRtrvlSleStpgeInfoService05` / `getMdcinRtrvlSleStpgelList05`(의약품 목록), `getMdcinRtrvlSleStpgeItem05`(의약품 상세), `getMdcinRtrvlSleStpgelEtcList05`(의약품외 목록), `getMdcinRtrvlSleStpgeEtcItem05`(의약품외 상세) | 실시간 | 1,194 | 공식문서확인 / **추가검증필요**: 페이지 상단 활용신청 수 0, 상세 메타 1,194 |
| 10 | 의약품 생산수입공급중단 정보 | 15057899 | `https://apis.data.go.kr/1471000/MdcinPrdctnIncmeSuplyService2` / `getMdcinPrdctnIncmeSuplyList` | 실시간 | 315 | 공식문서확인 / **추가검증필요**: 서비스명 `…Service2`(숫자 규칙 다름), 파라미터 camelCase(entpName, itemName) |
| 22·23 | 의약품 등 업체허가현황 (목록·상세) | 15095682 | `https://apis.data.go.kr/1471000/DrugEtcBsshBspmStusService01` / `getDrugBsshListInq01`(목록), `getDrugBsshItemInq01`(상세) | 실시간 | 370 | 공식문서확인 (응답항목 미추출) |
| 24 | 화장품 제조(판매)업 정보 | 15020628 | `https://apis.data.go.kr/1471000/CsmtcsMfcrtrInfoService02` / `getCsmtcsMfcrtrInfoList02` | 실시간 | 1,896 | 공식문서확인 / **추가검증필요**: 페이지 제목·설명은 "화장품 관련 정보(심사·보고품목 포함)"이나 오퍼레이션은 제조(판매)업 1개뿐 |
| 47 | 의약품 해외제조소 정보 | 15090422 | `https://apis.data.go.kr/1471000/OvseaMnfctrService` / `getOvseaMnfctrInq` | 실시간 | 137 | 공식문서확인 (운영 승인: **심의승인**) |
| 55 | 의약품GMP적합판정서발급현황 | 15097207 | `https://apis.data.go.kr/1471000/DrugGmpStbltJgmtIssuStusService` / `getDrugGmpStbltJgmtIssuStusInq` | 실시간 | 298 | 공식문서확인 (운영 승인: **심의승인**) |
| 61 | 의약외품 제품 허가정보 | 15095679 | `https://apis.data.go.kr/1471000/QdrgPrdtPrmsnInfoService03` / `getQdrgPrdtPrmsnInfoInq03` | 실시간 | 552 | **실제호출검증** (2026-11-17, 개발계정 승인, E절 참고) |

### A-1. 주요 요청변수 및 응답항목 (공식 상세 페이지 기재 기준)

**행정처분 (15058457)**
- 요청: `serviceKey`(필수), `entp_name`, `item_name`, `order`(Y=행정처분일 역순), `item_seq`, `pageNo`, `numOfRows`, `type`(xml 기본)
- 응답: `ADM_DISPS_SEQ`, `ENTP_NAME`, `ADDR`, `ENTP_SEQ`(업일련번호), `ITEM_NAME`, `BEF_APPLY_LAW`, `EXPOSE_CONT`, `ADM_DISPS_NAME`, `LAST_SETTLE_DATE`, `ITEM_SEQ`(품목기준코드), `RLS_END_DATE`, `totalCount`
- 참고문서: IROS_50_의약품행정처분서비스_v1.6.docx

**생산·수입공급중단 (15057899)**
- 요청: `serviceKey`(필수), `entpName`, `itemName`, `pageNo`, `numOfRows`, `type`
- 응답: `REPORT_PGS_CODE`, `SUSPEND_REPORT_SEQ`, `SUSPEND_REPORT_FLAG`, `ENTP_SEQ`, `ENTP_NAME`, `ENTP_NO`, `REPORT_ADDR`, `ITEM_SEQ`, `ITEM_NAME`, `EDI_CODE`(표준코드), `LAST_SUPPLY_DATE`, `SUSPEND_DATE`, `INV_DATE`, `INV_QTY`(재고량), `SUSPEND_REASON`, `SUPPLY_PLAN`, `REPORT_DATE`, `OPEN_CONFIRM_YN_NM` 등
- 샘플 totalCount: 268 (예시값이며 실제 건수 아님)

**해외제조소 (15090422)**
- 요청: `serviceKey`(필수), `pageNo`, `numOfRows`, `type`, `BSSH_NM`(수입업체명), `MFTR_NM`(제조소명)
- 응답: `BSSH_NM`, `MFTR_NM`, `MFTR_ADDR`, `MFTR_PRMSN_NO`(등록번호), `NATN_CD_NM`(국가), `MFTR_LATD`, `MFTR_LGTD`, `totalCount`
- 샘플 totalCount: 92,564 (예시값)

**GMP 적합판정서 (15097207)**
- 요청: `serviceKey`(필수), `pageNo`, `numOfRows`, `type`, `BSSH_NM`(업체명)
- 응답: `BSSH_NM`, `FCTR_ADDR`(공장소재지), `KGMP_BGMP_NAME`(완제/원료 구분), `GMP_INGR_MM_GROUP_NAME`(제형군/제조방법), `VLD_PRD_YMD`(유효기한), `totalCount`
- **제조소 고유번호 없음** (업체명·소재지 기반으로만 식별 가능 → 연계 시 주의)

**생산·수입실적 (15056880)**
- 응답 항목: 생산·수입연도, 생산금액(백만원), 수입금액(달러), 품목 기준 실적 (세부 필드는 상세 명세 펼쳐서 추가 확인 필요)

**의약품 제품 허가정보 (15095677)**
- 목록·상세·주성분 상세 3개 오퍼레이션. 설명상 포함 항목: 품목, 주성분, 제조원, 포장단위, 저장방법, 성상, 허가일자, 허가번호, 희귀의약품 여부. 세부 요청·응답 필드는 아직 미추출

**의약외품 제품 허가정보 (15095679)**
- 설명상 포함 항목: 품목명, 업체명, 품목분류번호, 효능·효과, 용법·용량, 사용상의 주의사항. 세부 필드는 미추출

**업체허가현황 (15095682)** / **화장품 제조(판매)업 (15020628)**: 설명 확인, 응답 필드 미추출

### A-2. 의약품안전나라 목록과 상세 페이지의 차이

- 목록 4번 `의약품 행정처분` → 15058457 (일치)
- 목록 7·12·30번 `의약품 제품허가목록 / 상세정보 / 주성분` → 모두 15095677 (**한 상세 페이지의 3개 오퍼레이션**)
- 목록 22·23번 `업소 허가정보 상세/목록` → 15095682 (**한 상세 페이지의 2개 오퍼레이션**)
- 목록 24번 `화장품 제조(판매)업 정보` → 15020628 (상세 페이지 제목은 "화장품 관련 정보")
- 목록 61번 의약외품 → 15095679 (일치)

## B. 나머지 49개 ID (공식문서확인, 2026-11-17)

공공데이터포털 상세 페이지에서 확인. **실제 호출은 미수행** (사용자 계정에 활용신청 없음). 49개 페이지 모두 정상 열람(삭제·폐지 없음). 업데이트 주기는 49개 모두 페이지 표기상 "실시간". 개발계정은 49개 모두 자동승인.

- **운영 승인**: 자 = 자동승인, 심 = 심의승인
- **공개 응답필드**: 페이지에 출력항목 표가 공개된 경우만 기재. Swagger형 페이지는 모델을 펼쳐야 하므로 "-"(미추출)
- 기본 URL은 `https://apis.data.go.kr/1471000/` 생략 (15056939만 기관코드 `1471057`)

| 목록 # | ID | 공식 API명 (목록명과 다르면 굵게) | 서비스 / 오퍼레이션 | 운영 승인 | 활용신청 수 | 수정일 | 공개 응답필드 |
|---|---|---|---|---|---|---|---|
| 1 | 15056780 | **의약품안전사용서비스(DUR)성분정보** | `DURIrdntInfoService03` / 7개: 병용금기, 임부금기, 용량주의, 투여기간주의, 노인주의, 특정연령대금기, 효능군중복 | 자 | 1,675 | 2025-09-16 | - |
| 2 | 15059486 | **의약품안전사용서비스(DUR)품목정보** | `DURPrdlstInfoService03` / 9개: 위 7종 + DUR품목정보, 서방정분할주의 | 자 | 2,789 | 2025-09-16 | - |
| 3 | 15056835 | 의약품 임상시험 정보 | `MdcinClincTestInfoService02` / `getMdcinClincTestInfoList02` | 자 | 735 | 2026-03-17 | - |
| 5 | 15056886 | 의약품공급부족 정보 | `MdcinSuplyLackService03` / `getMdcinSuplyLackList01` (서비스 03, 오퍼레이션 01로 버전 표기 다름) | 자 | 332 | 2025-09-16 | - |
| 6 | 15057623 | 의약품 특허정보 | `MdcinPatentInfoService2` / `getMdcinPatentInfoList2` | 자 | 683 | 2025-12-23 | - |
| 11 | 15057639 | 의약품 낱알식별 정보 | `MdcinGrnIdntfcInfoService03` / `getMdcinGrnIdntfcInfoList03` | 자 | 5,009 | 2025-11-10 | - |
| 13 | 15058963 | **마약류 약물 및 오남용 정보** | `NrcdGnrlzInfoService01/getNrcdGnrlzList` | 자 | 306 | 2025-09-03 | DRUG_NO, DRFSTF, DRFSTF_ENG, TYPE_CODE, PHARM, SIDE_EFFECT, MEDICATION |
| 14 | 15057931 | FDA 오렌지북 특허정보 | `FdaOrngbkPatentInfoService01/getFdaOrngbkPatentInfoList01` | 자 | 211 | 2025-09-19 | INGR_NAME, PRT_NAME, KOR_APPLY_NO, KOR_PAT_NO, KOR_NAME_OF_INVENTION, KOR_APPLICANT, KOR_EXP_DATE, KOR_STATUS |
| 15 | 15056710 | **국내소송 의약품(특허) 정보** | `DmstcLwstMdcinInfoService02` / `getMdcinRefreeSttusList02` (의약품심판현황) | 자 | 200 | 2025-09-22 | - |
| 16 | 15058137 | FDA Paragraph IV 대상 의약품 특허 정보 | `ParagraphIVTrgetMdcinService02` / `getParagraphIVSearchsList02` | 자 | 147 | 2025-09-22 | - |
| 17·25 | 15058041 | 마약류 및 원료물질 정보 | `NrcdNdRwmtrInfoService01/getNrcdNdRwmtrInfoList01` | 자 | 166 | 2025-09-03 | DATA_FLAG_NM, TREAT_APPROVAL_SEQ, ENTP_NAME, ENTP_ADDR, TREAT_START_DATE, TREAT_END_DATE |
| 18 | 15058034 | 의약품 재심사 정보 | `MdcinRejdgeService02/getMdcinRdjdgeList02` (서비스명 `Rejdge`, 오퍼레이션 `Rdjdge` 철자 다름) | 자 | 368 | 2026-08-10 | - |
| 19 | 15057382 | 의약품 재평가 정보 | `MdcinRevalService03` / `getMdcinRevalList03` | 자 | 245 | 2026-08-11 | - |
| 20 | 15059492 | 인체조직은행 정보 | `HmymBankInfoService01/getHmymBankList01` | 자 | 130 | 2025-09-01 | TISSUE_BANK_NO, TISSUE_BANK_NAME, TISSUE_BANK_P_NO, PERMIT_DATE, NEXT_PERMIT_UPDATE_DATE, ADDR, TREAT_ITEM, CLOSE_DATE |
| 21 | 15057935 | 희귀의약품 정보 | `RareMdcinInfoService02` / `getRareMdcinList02` | 자 | 548 | 2026-08-11 | - |
| 26·33 | 15095680 | 기능성화장품 보고품목정보 | `FtnltCosmRptPrdlstInfoService01` / `getRptEntpInq01`(업체), `getRptPrdlstInq01`(품목) | 심 | 1,393 | 2026-08-10 | - |
| 27 | 15058207 | **필수의약품내역** | `MdcEssntlItemInfoService03` / `getMdcEssntlItemList03` | 자 | 289 | 2025-09-16 | - |
| 28 | 15059182 | **의약품안전성서한 정보** | `DrugSafeLetterService02` / `getDrugSafeLetterList02` | 자 | 334 | 2025-09-16 | - |
| 29 | 15056518 | 실험동물제도 및 실험동물 시설정보 | `ExperAnimalExperAnimalFcltyInfoService02` / 3개: 동물실험시설, 실험동물공급자, 우수실험동물생산시설 | 자 | 172 | 2026-08-11 | - |
| 31 | 15056939 | 기능성화장품 심사품목 정보 (**제공: 식품의약품안전평가원**, 기관코드 1471057) | `FtnltCosmSrngPrdlstInfoService05` / `getSrngEntpInq05`, `getSrngPrdlstInq05` | 자 | 905 | 2026-08-20 | - |
| 32 | 15084883 | **감염병백신 국가출하승인정보** | `IcdVacinNatnShipmntAprvInfoService/getIcdVacinNatnShipmntAprvInfo` | 심 | 87 | 2025-09-03 | RCPT_PRCS_NO, SPCM_FORM_LIMS_PRDLST_NM, PRDLST_NM, MNFT_SALPS_NM, MNFT_NO, RESULT_TIME, PROVT_UNIT, VLD_PRD |
| 34 | 15058447 | **생동성인정품목조회** | `MdcBioEqInfoService01/getMdcBioEqList01` | 자 | 314 | 2025-09-08 | ITEM_SEQ, ITEM_NAME, ENTP_NAME, INGR_KOR_NAME, INGR_QTY, SHAPE_CODE_NAME, BIOEQ_PRODT_NOTICE_DATE |
| 35 | 15058806 | **대조약조회** | `MdcCompDrugInfoService04` / `getMdcCompDrugList04` | 자 | 350 | 2025-09-22 | - |
| 36 | 15057075 | **원료의약품등록(DMF)현황** | `MdcDmfInfoService02` / `getMdcDmfList02` | 자 | 971 | 2026-09-16 | - |
| 37 | 15063908 | **묶음의약품정보서비스** | `DrbBundleInfoService02` / `getDrbBundleList02` | 심 | 556 | 2025-09-22 | - |
| 38 | 15075057 | **의약품개요정보(e약은요)** | `DrbEasyDrugInfoService/getDrbEasyDrugList` | 심 | 6,142 | 2025-09-19 | entpName, itemName, itemSeq, efcyQesitm, useMethodQesitm, atpnWarnQesitm, atpnQesitm, intrcQesitm, seQesitm, depositMethodQesitm, openDe, updateDe, itemImage (**camelCase**) |
| 39 | 15090589 | 의약품 임상시험 계획 상세정보 | `ClncExamPlanDtlService03` / `getClncExamPlanDtlInq03` | 심 | 571 | 2026-08-11 | - |
| 40 | 15090368 | 의약품 임상시험 계획 선정기준 정보 | `ClncExamPlanSlctnStndrdService03` / `getClncExamPlanSlctnStndrdInq03` | 심 | 206 | 2026-08-11 | - |
| 41 | 15090376 | 의약품 임상시험 계획 제외기준 정보 | `ClncExamPlanExStndrdService03` / `getClncExamPlanExStndrdInq03` | 심 | 217 | 2026-08-11 | - |
| 42 | 15090384 | 의약품 임상시험 계획 시험책임자 정보 | `ClncExamPlanTestPscgService04` / `getClncExamPlanTestPscgInq04` | 심 | 265 | 2026-08-11 | - |
| 43–46 | 15090388 | 코로나 관련 의약품 임상시험 계획 상세 정보 | `InfectnClncExamPlanDtlServiceNew01` / 4개: 상세, 선정기준, 제외기준, 시험책임자 | 심 | 152 | 2026-08-10 | - |
| 48 | 15094473 | 마스크 허가현황 기본정보 | `MaskGradPrmsnStusListService/getMaskGradPrmsnStusListInq` | 심 | 132 | 2025-09-03 | PRDLST_SN, PRDLST_NM, BSSH_NM, GRADE, PRDLST_PRMSN_YMD, PRMSN_KIND_CD_NM, CLSF_NO_NM |
| 49–50 | 15094578 | 마스크 회수 제품 정보 | `MaskReclPrdtInfoService01/getMaskReclPrdtDtlInfoInq2` | 심 | 109 | 2025-09-03 | PRDLST_NM, TRAT_CONT, BSSH_NM, CNSGN_MANUF, PRDLST_PRMSN_YMD, CLSF_NO, BARCODE, PRDLST_SN 외 |
| 51 | 15094457 | 마스크 관련 업체 행정처분 정보 | `MaskAdmmInfoService/getMaskAdmmInfoInq` | 심 | 96 | 2025-09-03 | ENTP_NM, INDT_CD_NM, BSSH_PRMSN_NO, BSSH_ADDR, DSPS_YMD, RLS_END_YMD, RLS_VIOLT_CONT, DSPS_CONT, BASIS_ORDN_CONT, PRDLST_SN, PRDLST_NM |
| 52 | 15096118 | 감염병치료제 의약품제품정보 | `InfectnRemedyDrugPrdtInfoService/getInfectnRemedyDrugPrdtInfoInq` | 심 | 76 | 2025-09-19 | PRDLST_SN, PRDLST_NM, BSSH_NM, PRDLST_PRMSN_YMD |
| 53 | 15097199 | 통지의약품 정보 | `AvtsmtDrugService/getAvtsmtDrugInq` | 심 | 132 | 2025-09-19 | MCPN_CONT, CTNT_CONT, FOML_NM, PRDLST_PRMSN_APLY_DT |
| 54 | 15097204 | 우선판매품목허가 의약품 정보 | `PrtySalePrdlstPrmsnDrugService/getPrtySalePrdlstPrmsnDrugInq` | 심 | 141 | 2025-09-19 | MCPN_CONT, PRDLST_NM, CTNT_CONT, FOML_NM, PRDLST_PRMSN_APLY_DT, PRTY_SALE_DT |
| 56 | 15097208 | 안전상비의약품 정보 | `SafeStadDrugService/getSafeStadDrugInq` | 심 | 204 | 2025-09-11 | PRDLST_NM, BSSH_NM, VLD_PRD_YMD, STRG_MTH_CONT |
| 57 | 15098095 | **의약품 성분별 1일 최대투여량 정보** | `DayMaxDosgQyByIngdService/getDayMaxDosgQyByIngdInq` | 심 | 467 | 2025-09-14 | CPNT_CD, DRUG_CPNT_KOR_NM, DRUG_CPNT_ENG_NM, FOML_CD, FOML_NM, DOSAGE_ROUTE_CODE, DAY_MAX_DOSG_QY_UNIT, DAY_MAX_DOSG_QY |
| 58 | 15111774 | 화장품 원료성분정보 | `CsmtcsIngdCpntInfoService01` / `getCsmtcsIngdCpntInfoService01` | 심 | 1,759 | 2025-08-12 | - |
| 59–60 | 15111772 | 화장품 사용제한 원료정보 | `CsmtcsUseRstrcInfoService` / 2개: 사용제한 원료, 배합금지국가 | 심 | 685 | 2025-08-12 | - |
| 62–66 | 15107573 | **희귀필수의약품 정보** | `RareEsentMdcin` / 5개: 자가치료용 마약류, 치료용, 긴급도입 보험미등재, 긴급도입 보험등재, 긴급도입 마약류 | 심 | 142 | 2025-09-22 | - |
| 67 | 15106956 | 바이오의약품 해외임상승인현황 | `BioMdcinOvseaClncAprvStus` / `getBioMdcinOvseaClncAprvStus` | 심 | 105 | 2025-09-20 | - |
| 68 | 15106957 | **바이오의약품 해외허가제품정보** | `BioMdcinOvseaPrmisnPrduct` / `getBioMdcinOvseaPrmisnPrduct` | 심 | 80 | 2025-09-20 | - |
| 69 | 15106958 | 화장품 회수·판매중지 정보 | `CsmtcsRtrvlSleStpgeInfo` / `getCsmtcsRtrvlSleStpgeInfo` | 심 | 277 | 2025-08-12 | - |
| 70 | 15117412 | 혈액제제 제조소 정보 | `BldMdctMftrInfoService` / `getBldMdctMftrInfoService` | 심 | 46 | 2025-09-16 | - |
| 71 | 15117409 | 의약품 국내 특허현황 | `DrugDmstPtntStusService` / `getDrugDmstPtntStusService` | 심 | 176 | 2025-10-31 | - |
| 72 | 15124932 | 장애인 의약품 안전사용 정보(음성·수어영상) | `PwdbsDrugSafeUseInfoService` / `getPwdbsDrugSafeUseInfo` | 심 | 88 | 2025-09-22 | - |
| 73 | 15073980 | **희귀의약품성분 정보** | `RareDrugCpntService01/getRareDrugCpntInq01` | 심 | 172 | 2025-09-19 | RARE_DRUG_NO, MFTR_NM, TRGT_DISS_NM, PRDT_NM, MDCT_NM, DSGN_YMD, DSGN_RTRCN_YMD, RCPT_PRCS_NO, CPNT_SEQ, CPNT_CD, CPNT_KOR_NM |

### B-1. 목록(nedrug)과 공식 페이지의 차이

- **목록명과 공식명이 다른 경우 15건** (표의 굵은 글씨). 예: 목록 "의약품심판현황" → 공식 "국내소송 의약품(특허) 정보", 목록 "긴급도입·자가치료용 의약품" 5건 → 공식 "희귀필수의약품 정보" 1개 API의 5개 오퍼레이션
- **목록 73건 = 오퍼레이션 단위, 공식 59개 = API(상세 페이지) 단위**. 목록이 같은 API를 오퍼레이션별로 나눠 적은 경우: 15107573(5건), 15090388(4건), 15095677(3건), 15095682·15095680·15094578·15111772·15058041(각 2건)
- 15056939는 제공기관이 식품의약품안전평가원(기관코드 1471057)으로 다른 API와 다름

### B-2. 공개된 응답필드 기준 식별자 (명세 기준, 실측 아님)

- `ITEM_SEQ` 또는 `itemSeq`: 생동성인정품목(15058447), e약은요(15075057, camelCase)
- `PRDLST_SN`(품목일련번호): 마스크 3종, 감염병치료제 → ITEM_SEQ와 같은 체계인지 **미확인**
- `CPNT_CD`(성분코드): 1일최대투여량(15098095), 희귀의약품성분(15073980) → 제품허가 주성분의 `MTRAL_CODE`와 같은 체계인지 **미확인**
- 업체 식별자: 대부분 업체명 문자열만 공개. `BIZRNO`는 공식 명세에 없지만 승인 API 10개에서는 실제로 반환되었으므로, 승인 후 실측 필요

원본 목록: [data/nedrug_list_73.tsv](../data/nedrug_list_73.tsv)

## C. 공식 정보 간 불일치 및 추가 확인 사항

1. 상단 활용신청 수(0~3 등)와 상세 메타의 활용신청 수(수백~만 단위)가 서로 다름. 어느 쪽이 공식 집계인지 불명확 → **추가검증필요**
2. 업데이트 주기가 "실시간"으로 표시된 API가 많으나, 생산·수입실적은 "연간"으로 표시됨. 실제 갱신 시점은 실제 호출로 확인 필요
3. 공급중단 API(15057899)의 서비스명이 `…Service2`이고 파라미터가 camelCase로 다른 API와 명명 규칙이 다름
4. 회수·판매중지(15059114)의 오퍼레이션명에 `Stpgel`처럼 철자가 다른 항목 있음. 호출 시 실제 경로와 대조 필요
5. 화장품 상세(15020628)는 페이지 설명과 오퍼레이션 수가 다름
6. 상세 페이지 설명문 중 "활용 사례"는 제3자 서비스 소개이며 데이터 사실이 아님 (본 카탈로그에서 사용하지 않음)
7. 목록 페이지의 "공공데이터 파일 다운로드 서비스 종료" 안내: 파일 다운로드는 종료되었고 식의약데이터포털(csv)로 대체. OpenAPI 제공은 별도 확인됨 (목록 전체가 OpenAPI 형식)

## E. 활용신청 현황 및 실제 호출 검증 (2026-11-17, 사용자 로그인 후)

### E-1. 활용신청 현황 (공공데이터포털 마이페이지 > 활용신청 현황)

| 항목 | 값 |
|---|---|
| 전체 신청 | 1건 (승인 1, 신청·보류·반려 0, 만료·중지 0) |
| 승인 API | 식품의약품안전처_의약외품 제품 허가 정보 (15095679) |
| 계정 / 심의 | 개발계정 / 자동승인 |
| 활용기간 | 2026-11-17 ~ 2028-11-17 |
| 상세기능 / 일일 트래픽 | `/getQdrgPrdtPrmsnInfoInq03` / 10,000 |
| 나머지 9개 선정 API | 2026-11-17 사용자 승인 후 개발계정 신청 제출 → **9개 모두 즉시 [승인]** (활용기간 ~2028-11-17). 활용목적 "웹 사이트 개발", 전체 상세기능 선택 |
| 현재 승인 합계 | **10건** (모두 개발계정, 일일 10,000회/오퍼레이션) |

### E-2. 의약외품 제품 허가정보 실제 호출 결과

호출: `GET {EndPoint}/getQdrgPrdtPrmsnInfoInq03?serviceKey=***&pageNo=1&numOfRows=N&type=json` (인증키는 기록하지 않음). 총 5회 호출.

| 검증 항목 | 결과 |
|---|---|
| HTTP / resultCode | 200 / `00` (`NORMAL SERVICE.`) |
| 전체 건수 (totalCount) | **22,916** (조사 시점) |
| numOfRows 2 / 100 / 500 | 모두 정상, 요청 수만큼 반환 (상한은 미확인) |
| JSON 구조 | `header{resultCode,resultMsg}`, `body{pageNo,totalCount,numOfRows,items[]}`. `items`의 각 원소는 `{"item": {...}}`로 한 번 더 감싸져 있음 |
| 상태값 `CANCEL_CODE_NAME` | 첫 500건에서 `정상`, `취하`, `폐업` 확인 → **취하·폐업 품목도 응답에 포함됨** |
| `BIZRNO` 누락 | 첫 500건 중 3건 비어 있음 |

실제 응답 필드 (공식 페이지 설명에는 없던 필드 포함):

| 필드 | 의미 (응답값 기준 해석) | 비고 |
|---|---|---|
| `ITEM_SEQ` | 품목기준코드 | 예: `197100246` |
| `ITEM_NAME` | 품목명 | |
| `ENTP_NAME` | 업체명 | |
| `ITEM_PERMIT_DATE` | 허가일자 | 형식 `YYYY-MM-DD` |
| `ITEM_NO` | 품목 번호 | 의미 추가 확인 필요 |
| `CANCEL_CODE_NAME` | 상태 (정상/취하/폐업) | |
| `CANCEL_DATE` | 취하일자 | 형식 `YYYYMMDD` (**허가일자와 형식 다름**) |
| `MAIN_INGR` / `ADIT_INGR` | 주성분 / 첨가제 | null 가능 |
| `CLASS_NO` / `CLASS_NO_NAME` | 품목 분류번호 / 분류명 | 예: `33800` / `[33800]반창고` |
| `PERMIT_KIND_CODE_NM` | 허가 종류 | 예: `허가` |
| `INDUTY_CODE` | 업종 | 예: `제조` (코드가 아닌 명칭이 들어 있음) |
| `MANUF_COUNTRY_NAMES` | 제조국 | null 가능 |
| `EE_DOC_DATA` / `UD_DOC_DATA` / `NB_DOC_DATA` | 효능효과 / 용법용량 / 사용상주의사항 | **JSON 안에 XML 문자열**(DOC/SECTION/ARTICLE/PARAGRAPH, CDATA) → 파싱 필요 |
| `ENTP_NO` | 업허가번호 | 예: `0476` |
| `ENTP_SEQ` | 업 일련번호 | 행정처분·공급중단 API와 같은 필드명 |
| `BIZRNO` | 사업자등록번호 | 공식 설명에 없던 필드. 업체 연계 핵심 후보 |

공식 문서와 실제 응답의 차이:
- 공식 설명의 "품목 분류번호" → 실제 `CLASS_NO`
- 공식 설명에 없는 `ENTP_SEQ`, `ENTP_NO`, `BIZRNO`, `CANCEL_CODE_NAME`, `CANCEL_DATE`, `MAIN_INGR` 등이 실제로 제공됨
- 날짜 형식이 필드마다 다름 (`YYYY-MM-DD` / `YYYYMMDD`)
- 검색용 요청변수(품목명·업체명 등)는 상세 명세를 아직 펼치지 않아 미확인

### E-3. 9개 API 실제 호출 결과 (2026-11-17, 승인 직후)

호출 조건: `pageNo=1&numOfRows=2&type=json` (필드 확인), 일부 `numOfRows=100` (형식 점검). 계정 공통 일반 인증키 1개로 모든 API 호출 성공. 총 호출 약 26회.

| API / 오퍼레이션 | HTTP/코드 | totalCount (조사 시점) | items 구조 | 실제 응답 필드 |
|---|---|---|---|---|
| 행정처분 `getMdcinExaathrList04` | 200/00 | **538** | flat | ADM_DISPS_SEQ, ENTP_NAME, ADDR, ENTP_NO, ITEM_NAME, BEF_APPLY_LAW, EXPOSE_CONT, ADM_DISPS_NAME, LAST_SETTLE_DATE, ITEM_SEQ, RLS_END_DATE, BIZRNO |
| 제품허가 목록 `getDrugPrdtPrmsnInq08` | 200/00 | **42,721** | flat | ITEM_SEQ, ITEM_NAME, ITEM_ENG_NAME, ENTP_NAME, ENTP_ENG_NAME, ENTP_SEQ, ENTP_NO, ITEM_PERMIT_DATE, INDUTY, PRDLST_STDR_CODE, SPCLTY_PBLC, PRDUCT_TYPE, PRDUCT_PRMISN_NO, ITEM_INGR_NAME, ITEM_INGR_CNT, BIG_PRDT_IMG_URL, PERMIT_KIND_CODE, CANCEL_DATE, CANCEL_NAME, EDI_CODE, BIZRNO |
| 제품허가 상세 `getDrugPrdtPrmsnDtlInq08` | 200/00 | 42,721 | flat | ITEM_SEQ, CNSGN_MANUF(위탁제조), ETC_OTC_CODE, CHART, BAR_CODE, MATERIAL_NAME, STORAGE_METHOD, VALID_TERM, REEXAM_TARGET, REEXAM_DATE, PACK_UNIT, EDI_CODE, NEWDRUG_CLASS_NAME, CANCEL_DATE, CANCEL_NAME, CHANGE_DATE, NARCOTIC_KIND_CODE, EE/UD/NB/PN_DOC_DATA, MAIN_ITEM_INGR, ATC_CODE, RARE_DRUG_YN, DATA_PROTECT_START/END_DATE, BIZRNO 외 |
| 제품허가 주성분 `getDrugPrdtMcpnDtlInq08` | 200/00 | **125,604** (성분 행 단위) | flat | ENTRPS_PRMISN_NO, ENTRPS, PRDUCT, MTRAL_SN, MTRAL_CODE, MTRAL_NM, QNT, INGD_UNIT_CD, ITEM_SEQ, MAIN_INGR_ENG, BIZRNO, CPNT_CTNT_CONT, TAMT_SEQ |
| 생산·수입실적 `getMdcinPrdctnImportrstList02` | 200/00 | **176,133** (품목×연도×구분) | item-wrapped | ITEM_SEQ, DATE_YEAR, ITEM_NAME, ENTP_NAME, ENTP_SEQ, RESULT_PART(생산/수입), AMT, BIZRNO |
| 회수 의약품 목록 `getMdcinRtrvlSleStpgelList05` | 200/00 | **994** | item-wrapped | PRDUCT, ENTRPS, RTRVL_RESN, ENFRC_YN(Y/N), RTRVL_CMMND_DT, RECALL_COMMAND_DATE, ITEM_SEQ, BIZRNO, STD_CD |
| 회수 의약품외 목록 `getMdcinRtrvlSleStpgelEtcList05` | 200/00 | 226 | item-wrapped | PRDUCT, ENTRPS, RTRVL_RESN, ENFRC_YN, RTRVL_CMMND_DT, BIZRNO |
| 공급중단 `getMdcinPrdctnIncmeSuplyList` | 200/00 | **1,339** | flat | 공식 명세 필드 전부 + BIZRNO |
| 업체허가 목록 `getDrugBsshListInq01` | 200/00 | **2,872** | flat | INDUTY, ENTRPS, PRMISN_DT, ADRES, PRMISN_NO, BIZRNO |
| 업체허가 상세 `getDrugBsshItemInq01` | 200/00 | 1,081 | flat | ENTRPS, INDUTY, PRMISN_NO, PRMISN_DT, SN, FCTRY_NM, FCTRY_ADDR1, FCTRY_ADDR2, BIZRNO (공장 단위) |
| 화장품 제조(판매)업 `getCsmtcsMfcrtrInfoList02` | 200/00 | 33,155 | flat | INDUTY, ENTP_SEQ, ENTP_NAME, ENTP_PERMIT_DATE, FACTORY_ADDR, BIZRNO |
| 해외제조소 `getOvseaMnfctrInq` | 200/00 | **13,629** | flat | BSSH_NM, MFTR_NM, MFTR_ADDR, MFTR_PRMSN_NO, NATN_CD_NM, MFTR_LATD, MFTR_LGTD, BIZRNO |
| GMP 적합판정 `getDrugGmpStbltJgmtIssuStusInq` | 200/00 | **569** | flat | BSSH_NM, FCTR_ADDR, KGMP_BGMP_NAME, GMP_INGR_MM_GROUP_NAME, VLD_PRD_YMD, BIZRNO |

미호출: 회수 상세 2종(`…Item05`, `…EtcItem05`) — 상세 조회용 키 파라미터 확인 후 시험 예정.

형식 점검 (각 API 첫 100건):

| 항목 | 결과 |
|---|---|
| `BIZRNO` | 8개 API 모두 **100/100건 10자리 숫자, 누락 0** (의약외품만 500건 중 3건 누락) |
| 날짜 형식 | 대부분 `YYYYMMDD`. 예외: GMP `VLD_PRD_YMD`=`YYYY-MM-DD`, 의약외품 `ITEM_PERMIT_DATE`=`YYYY-MM-DD`, 회수 `RTRVL_CMMND_DT`=14자리(`YYYYMMDDhhmmss`) |
| 생산·수입실적 | 첫 100건은 모두 2025년·생산. `AMT` 소수 포함 (생산 단위: 백만원, 공식 설명 기준) |
| 회수 `ENFRC_YN` | Y, N 확인 |

공식 문서와 실제 응답의 차이 (중요):
1. **모든 API가 `BIZRNO`(사업자등록번호)를 반환**하나 공식 상세 페이지 명세에는 기재되어 있지 않음
2. 행정처분: 명세에는 `ENTP_SEQ`가 있으나 실제 응답에는 **없음**, 대신 `ENTP_NO`, `BIZRNO`가 있음
3. 해외제조소 totalCount 13,629 / GMP 569 / 공급중단 1,339 → 공식 페이지 샘플값(92,564 / 545 / 268)과 다름 (샘플은 예시값)
4. 행정처분 538건은 전체 이력이 아닌 공개기간(`RLS_END_DATE`) 내 건으로 추정됨 → **추가검증필요** (과거 처분이 공개 종료 후 사라지는지 수집 이력으로 확인)
5. items 구조가 API마다 다름 (flat 배열 / `{"item":{}}` 래핑) → 수집기에서 두 형태 모두 처리 필요
6. 같은 의미의 필드명이 API마다 다름: 업체명 `ENTP_NAME`/`ENTRPS`/`BSSH_NM`, 품목명 `ITEM_NAME`/`PRDUCT`, 표준코드 `EDI_CODE`/`STD_CD`

### E-4. 권장 등급 14개 활용신청 및 실제 호출 (2026-11-17, 사용자 승인 후)

활용신청: 14개 개발계정 신청 제출 → **14개 모두 즉시 승인**. 계정 전체 승인 **24건** (신청·보류·반려 0).
호출 조건: `pageNo=1&numOfRows=100&type=json`. 22개 오퍼레이션 중 **21개 200/00 성공**.

| API (ID) / 오퍼레이션 | 결과 | totalCount | 구조 | BIZRNO (100건 중) | 주요 식별자 |
|---|---|---|---|---|---|
| DUR 품목정보 (15059486) `getDurPrdlstInfoList03` | 200/00 | 23,468 | flat | 100 | ITEM_SEQ, EDI_CODE |
| DUR 병용금기 `getUsjntTabooInfoList03` | 200/00 | **790,684** | flat | 100 | ITEM_SEQ, MIXTURE_ITEM_SEQ, INGR_CODE |
| DUR 노인주의 `getOdsnAtentInfoList03` | 200/00 | 2,240 | flat | **0 (필드 없음)** | ITEM_SEQ, INGR_CODE |
| DUR 특정연령대금기 `getSpcifyAgrdeTabooInfoList03` | 200/00 | 2,737 | flat | 0 (필드 없음) | ITEM_SEQ, INGR_CODE |
| DUR 용량주의 `getCpctyAtentInfoList03` | 200/00 | 6,645 | flat | 0 (필드 없음) | ITEM_SEQ, INGR_CODE |
| DUR 투여기간주의 `getMdctnPdAtentInfoList03` | 200/00 | 575 | flat | 0 (필드 없음) | ITEM_SEQ, INGR_CODE |
| DUR 효능군중복 `getEfcyDplctInfoList03` | 200/00 | 7,076 | flat | 100 | ITEM_SEQ, INGR_CODE |
| DUR 서방정분할주의 `getSeobangjeongPartitnAtentInfoList03` | 200/00 | 2,195 | flat | 100 | ITEM_SEQ |
| DUR 임부금기 `getPwnmTabooInfoList03` | 200/00 | 16,112 | flat | 0 (필드 없음) | ITEM_SEQ, INGR_CODE |
| 의약품공급부족 (15056886) | 200/00 | 778 | item-wrapped | 100 | ITEM_SEQ, ENTP_SEQ, EDI_CODE, SHORT_SUPPLY_REPORT_SEQ |
| 의약품안전성서한 (15059182) | 200/00 | 322 | flat | 0 (필드 없음) | SAFT_LETT_NO (품목·업체 식별자 없음) |
| 의약품 재심사 (15058034) | 200/00 | 112,441 | flat | 100 | BIZRNO, ITEM_NO (**ITEM_SEQ 아님**, 값 예: "1") |
| 의약품 재평가 (15057382) | 200/00 | 64,967 | item-wrapped | 100 | BIZRNO, ENTP_NO, ITEM_NO (ITEM_SEQ 아님) |
| 희귀의약품 정보 (15057935) | **403** | - | - | - | `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`(코드 30). 승인 직후 게이트웨이 미반영으로 판단 → **재시도 필요** |
| 의약품 특허정보 (15057623) | 200/00 | 125,789 | flat | 0 (필드 없음) | ITEM_SEQ, DOMESTIC_PATENT_NO |
| 의약품 국내 특허현황 (15117409) | 200/00 | 8,158 | flat | 0 (필드 없음) | PTNT_PRDLST_CRTR_CD (9자리, ITEM_SEQ와 같은 형식 — 일치 여부 미확인), PTNT_NO |
| 우선판매품목허가 (15097204) | 200/00 | 647 | flat | 0 (필드 없음) | **식별자 없음** (성분·품목명 문자열만) |
| 생동성인정품목 (15058447) | 200/00 | 11,995 | flat | 100 | ITEM_SEQ |
| 원료의약품등록 DMF (15057075) | 200/00 | 9,215 | flat | 100 | DMF_PERMIT_NO, BIZRNO |
| 의약품 임상시험 정보 (15056835) | 200/00 | 14,436 | flat | 0 (필드 없음) | CLNC_TEST_SN |
| 임상시험 계획 상세 (15090589) | 200/00 | 8,273 | flat | 0 (필드 없음) | CLNC_TEST_SN |
| 묶음의약품정보 (15063908) | 200/00 | 16,282 | item-wrapped | 0 (필드 없음) | cnsgnItemSeq (9자리, ITEM_SEQ 형식), trustHiraPrductCode, trustAtcCode (**camelCase**) |

공식 문서와 실제 응답의 차이 / 발견 사항:
1. 생동성인정품목·DMF는 상세 페이지 포맷이 "XML"로 표기되어 있으나 `type=json` 요청에 **JSON으로 정상 응답**
2. BIZRNO는 이번 14개 중 **7개 API에만** 있음 (DUR 일부 오퍼레이션, 공급부족, 재심사, 재평가, 생동성, DMF). 앞의 10개처럼 "전부 반환"은 아님
3. DUR 품목정보는 같은 서비스 안에서도 오퍼레이션마다 BIZRNO 유무가 다름
4. 재심사·재평가의 `ITEM_NO`는 작은 정수("1", "4", "17")로 품목기준코드가 아님 → 품목 연계는 BIZRNO + 품목명 문자열(검증대기)
5. 임상시험 정보와 계획 상세는 둘 다 `CLNC_TEST_SN`을 가지나, 각 첫 500건끼리는 겹치는 값 0건(정렬·범위 차이 가능) → 동일 키인지 **미확인**
6. 묶음의약품은 필드명이 camelCase이고 위탁(trust)·수탁(cnsgn) 두 품목을 한 행에 담음
7. DUR 병용금기는 79만 건으로 수집 시 페이지 수가 매우 많음 (일일 호출 한도 고려 필요)

## D. 확인되지 않은 항목 (추정하지 않음)

- 희귀의약품 정보(15057935) 실제 응답 (게이트웨이 반영 후 재시도)

- 각 API의 검색 요청변수 동작, numOfRows 상한, 일일 호출 제한 초과 시 응답
- 행정처분 공개 종료 데이터의 처리 방식
- 목록 상세 49개 ID의 명세 전체
- 요청변수 전체 목록, 응답 전체 필드 (상세 명세 펼침 필요)
- 실제 응답 구조, 전체 건수, 페이지 크기 제한, 호출 제한 횟수 (실제 호출 필요)
- 목록 상세 49개 ID의 명세 전체

## E-5. 제품허가 상세 요청변수 실측 (2026-11-18, Actions probe run 44208814923)

공식 명세(data.go.kr 15095677 Swagger)의 상세 오퍼레이션 요청변수: `item_name`, `entp_name`, `item_permit_date`, `entp_no`, `bar_code`, `item_seq`, `start_change_date`, `end_change_date`, `edi_code`, `atc_code`, `bizrno`, `rare_drug_yn`, `main_item_ingr`.

| 시험 | 결과 |
|---|---|
| `start_change_date=20261101`, `end_change_date=20261118` | **동작함.** 326건, CHANGE_DATE 20261102~20261117 (범위 안만 반환) |
| 같은 기간을 `YYYY-MM-DD`로 | 0건 → 형식은 **YYYYMMDD만** |
| `start_change_date`만 지정 | 326건 (끝 날짜 생략 가능) |
| 2026-10-01~10-31 | 1,130건 → 한 달 약 1,100건, 하루 수십 건 변경 |
| `item_seq=195500005` | **동작함.** 1건, 약 2초 |
| `item_permit_date=2026` | 1,248건이지만 CHANGE_DATE 빈 값 365건 등 의미 불명확 → **추가검증필요**, 사용 안 함 |
| 응답 크기 | 상세 100건 1,441KB (목록 100건 64KB의 약 22배). 변경 품목 326건은 100,572KB (건당 약 300KB) |
| 큰 필드 (상세 100건) | `NB_DOC_DATA`(사용상 주의사항 문서) **73.3%**, `UD_DOC_DATA`(용법용량) 6.8%, `GBN_NAME`(변경 이력 문자열) 5.8%, `EE_DOC_DATA`(효능효과) 3.6% |

확인 못 한 것: 신규 허가 품목에도 CHANGE_DATE가 채워지는지 (허가일 시험에서 빈 값이 있었음). → 신규 품목은 목록에서 새 ITEM_SEQ를 찾아 `item_seq`로 따로 받는 방식으로 대비.
