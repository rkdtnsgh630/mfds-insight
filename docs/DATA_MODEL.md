# 데이터 모델

갱신: 2026-11-17

원칙: API별 원본 데이터와 표준화 데이터를 분리한다. 현재 구현된 것은 **원본·관리 계층**이며, 표준화 계층은 원본이 쌓인 뒤 실제 값을 확인하고 만든다.

## 1. 구현됨 (collector/store.py)

| 테이블 | 내용 |
|---|---|
| `api_source` | API id, 이름, data.go.kr ID, 경로, 키 필드, 등급, 출처 URL |
| `collect_run` | 실행 단위 이력 (시작·종료, 상태, 트리거, 대상, API 호출 수) |
| `collect_api_run` | API별 실행 결과 (totalCount, 페이지, 수집·추가·변경·결측·재등장·중복·키충돌 건수, 비고, 오류) |
| `raw_record` | 원본 레코드 JSON. 키 `(api_id, record_key)`, 해시, 최초·최근 수집 실행·시각, `is_present` |
| `change_log` | `added` / `updated` / `removed` / `reappeared`, 변경 전후 JSON, 실행 id, 시각 |

### 레코드 식별 (record_key)

- `apis.py`의 `key` 필드가 있으면 그 값들을 `|`로 이어 쓴다 (예: 생산실적 `ITEM_SEQ|DATE_YEAR|RESULT_PART`).
- `key`가 없으면 레코드 전체 해시(`h:…`)를 쓴다. 이 경우 값이 바뀌면 `removed` + `added`로 기록된다.
- 같은 실행 안에서 키가 겹치는데 내용이 다르면 `키#해시12자리`로 구분하고 `key_collisions`에 센다. 내용까지 같으면 `duplicates`로 세고 건너뛴다.
- 키 충돌·중복 건수는 실제 수집 후 키 설계를 고치는 근거로 쓴다.

### 변경 이력 규칙

- API별 첫 **완전 수집**은 기준선이며 `change_log`를 남기지 않는다 (과거 이력을 만들어 내지 않음).
- 증분 수집(`incremental` 설정, 현재 제품허가 상세)은 상태 `incremental`로 기록하고 결측(removed) 판정을 하지 않는다. 결측 점검은 월 1회 `--full` 실행에서 한다.
- `drop_fields`로 지정한 필드는 저장·해시에서 빠진다. 나중에 지정된 경우 기존 원본에서도 지우되 변경 이력은 남기지 않는다 (저장 방식 변경이지 데이터 변경이 아님).
- `removed`는 완전 수집일 때만 판정한다. 이번 건수가 직전 존재 건수의 50% 미만이면 API 장애 가능성이 있으므로 판정을 보류하고 비고에 남긴다.
- `removed`는 "API에서 조회되지 않음"이다. 실제 취하·삭제 여부는 허가 상태 필드(예: `CANCEL_NAME`)로 따로 판단한다.

## 2. 표준화 계층 (설계안, 미구현)

| 테이블 | 기준 키 | 출처 API |
|---|---|---|
| `company` | `BIZRNO` | 업체허가, 제품허가, 행정처분, GMP, 해외제조소 등 |
| `product` | `ITEM_SEQ` | 제품허가, 의약외품, DUR 품목 |
| `factory` | 업체허가 상세의 공장 (BIZRNO + 공장명·주소) | 업체허가 상세, GMP(주소 문자열 → 검증대기) |
| `production_stat` | `ITEM_SEQ` + 연도 + 구분 | 생산·수입실적 |
| `admin_action` | `ADM_DISPS_SEQ` | 행정처분 |
| `recall` | `ITEM_SEQ` + 명령일 | 회수·판매중지 |
| `supply_issue` | 보고번호 | 공급중단, 공급부족 |
| `link_candidate` | — | 문자열 추정 연계와 그 상태 (공식식별자일치 / 문자열추정 / 검증대기 / 연계불가) |
| `user`, `watch_*`, `user_alert` | — | Phase 5 |

## 3. 날짜 형식 정규화 (실측 기준)

`YYYYMMDD`(대부분), `YYYY-MM-DD`(GMP 유효기한, 의약외품 허가일), 14자리 `YYYYMMDDhhmmss`(회수 명령일시) 세 가지가 섞여 있다. 원본은 그대로 두고 표준화 계층에서 ISO 날짜로 바꾼다.
