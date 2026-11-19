# MFDS INSIGHT

식품의약품안전처(MFDS) 공공데이터 API를 연계해 국내 제약산업·의약품·GMP·행정처분·안전정보를 검색·분석하는 공개 웹 플랫폼 (가칭).

## 현재 상태

- Phase 1 (API 조사): 공식 목록 59개 API 명세 확인, 24개 활용 승인, 23개 실제 호출 검증 → [docs/API_CATALOG.md](docs/API_CATALOG.md)
- Phase 2 (수집 기반): 수집기 1차 구현 — 이 저장소의 `collector/`
- 홈페이지: https://rkdtnsgh630.github.io/mfds-insight/ (GitHub Pages, 검색엔진 비노출 `noindex`). 수집 → site 워크플로가 끝나면 자동 배포

## 수집기

GitHub Actions에서 매일 02:43(KST) 실행된다. PC에 아무것도 설치할 필요가 없다.

```
collector/
  apis.py    수집 대상 API 등록부 (실제 호출로 검증된 경로만)
  client.py  공공데이터포털 호출 (재시도, 응답 구조 정규화, 인증키 비노출)
  store.py   SQLite 저장 (원본 레코드, 수집 이력, 변경 이력)
  run.py     실행 진입점
tests/       단위 시험 (네트워크 없이 실행)
.github/workflows/collect.yml
```

- 표준 라이브러리만 사용한다 (추가 패키지 없음).
- 수집 결과 DB(`mfds.sqlite.gz`)는 저장소에 커밋하지 않고 **Release `data-latest`** 에 올린다. 다음 실행은 이 DB를 내려받아 이어서 쌓는다.
- 각 API의 첫 완전 수집은 기준선이고, 그 뒤부터 `change_log`에 추가·변경·결측·재등장을 기록한다.
- API에서 조회되지 않게 된 레코드는 `is_present=0`으로만 표시한다. 삭제·취하로 단정하지 않는다.

### 처음 설정 (한 번만)

1. 저장소 **Settings → Secrets and variables → Actions → New repository secret**
2. Name: `MFDS_SERVICE_KEY`, Secret: 공공데이터포털 마이페이지의 일반 인증키 (Encoding/Decoding 어느 쪽이든 가능)

### 수동 실행

**Actions → collect → Run workflow**

| 입력 | 의미 | 기본값 |
|---|---|---|
| apis | `tier:core`, `tier:hold`, `tier:core+hold`, `all`, 또는 `gmp,dmf`처럼 API id 나열 | `tier:core` |
| max_pages | API당 최대 페이지. 0이 아니면 시험 실행으로 보고 DB를 게시하지 않음 | `0` |
| rows | 페이지당 건수 | `500` |

확정된 사이트 화면 7개가 쓰는 `core` 11개를 매일 02:43 KST에 수집한다. 제품허가 상세는 매일은 변경분만(최근 성공일-7일 이후 변경 + 목록의 신규 품목) 받고, 매월 1일 03:47 KST에 전체(`--full`, 결측 점검)를 받는다. 상세의 문서 본문 3종(NB/UD/EE_DOC_DATA)은 저장하지 않는다. `hold`(보류 12개)는 메뉴 채택 시 수동 실행하고, `excluded`(DUR·의약외품·화장품·주성분 상세 등 13개)는 등록만 유지한다. 근거: docs/DASHBOARD_DESIGN.md

## 문서

- [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) 확정 요구사항
- [docs/API_CATALOG.md](docs/API_CATALOG.md) API 조사 결과
- [docs/API_EVALUATION.md](docs/API_EVALUATION.md) 활용 가치 평가
- [docs/API_RELATIONSHIPS.md](docs/API_RELATIONSHIPS.md) API 간 연계 가능성
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md) 데이터 모델
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 시스템 구조
- [docs/DASHBOARD_DESIGN.md](docs/DASHBOARD_DESIGN.md) 대시보드 설계 초안
- [docs/DECISIONS.md](docs/DECISIONS.md) 주요 결정
- [docs/PROGRESS.md](docs/PROGRESS.md) 진행 현황
- [docs/NEXT_STEPS.md](docs/NEXT_STEPS.md) 다음 작업

## 보안

인증키는 GitHub Secrets에만 둔다. 코드·문서·로그·DB에 기록하지 않는다.

## 데이터 출처

모든 데이터는 공공데이터포털(data.go.kr)의 식품의약품안전처 OpenAPI에서 수집한다. 각 API의 출처 URL은 DB의 `api_source.source_url`과 [docs/API_CATALOG.md](docs/API_CATALOG.md)에 있다.
