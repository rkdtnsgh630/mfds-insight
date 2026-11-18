# 시스템 구조

갱신: 2026-11-17

## 확정된 부분 (사용자 결정: "GitHub에 올려서 운영")

| 영역 | 선택 | 근거 |
|---|---|---|
| 소스 저장소 | GitHub 공개 저장소 `rkdtnsgh630/mfds-insight` | 사용자 지시. 공개 저장소면 Actions·Pages 무료 |
| 수집 실행 | GitHub Actions (매일 03:00 KST + 수동 실행) | PC 설치 불필요, 무료 |
| 수집기 언어 | Python 3.12, 표준 라이브러리만 | Actions 기본 제공, 의존성 관리 불필요 |
| 데이터 저장 | SQLite 파일, Release `data-latest`에 gzip으로 게시 | 무료. 저장소에 커밋하지 않아 git 이력 비대화 방지 (Release 파일 한도 2GB) |
| 인증키 | GitHub Secrets `MFDS_SERVICE_KEY` | 코드·로그·사이트에 노출 안 됨 |

## 미확정 (다음 단계에서 결정)

| 영역 | 후보 | 메모 |
|---|---|---|
| 홈페이지 | GitHub Pages 정적 사이트 (React + TypeScript + Tailwind + ECharts) | 수집 DB에서 화면용 JSON을 미리 만들어 배포하는 방식 검토 |
| 검색 | 사전 생성 인덱스 또는 브라우저 SQLite(sql.js) | 데이터 크기 측정 후 결정 |
| 회원 기능 | Supabase Auth 등 | Phase 5. 외부 계정 생성은 사용자 승인 필요 |
| 운영 DB 전환 | PostgreSQL | 회원 기능·대용량 검색이 필요해지면 검토. SQLite 스키마는 이식 가능하게 작성 |

## 수집 흐름

```
GitHub Actions (cron / 수동)
  1. 단위 시험 (tests/)
  2. Release data-latest 에서 이전 mfds.sqlite.gz 내려받기 (없으면 새로 시작)
  3. collector.run: API별 전 페이지 수집 → raw_record upsert → change_log 기록
  4. mfds.sqlite.gz + last_run.json 을 Release data-latest 에 덮어쓰기
     (max_pages 시험 실행은 게시하지 않음)
```

## 제약과 대응

| 제약 | 대응 |
|---|---|
| 오퍼레이션당 일일 10,000회 호출 | 페이지당 500건 기준, 가장 큰 DUR 병용금기도 약 1,600회 |
| Actions 작업 최대 6시간 | `timeout-minutes: 340`, 매일 core 10개(약 12분), 매월 1일 slow 1개(약 80분). 보류(hold)는 수동 실행 |
| 공개 저장소 60일 무활동 시 예약 실행 중지 | 커밋이 없으면 수동으로 재활성화 필요 |
| Release 파일 2GB | gzip 압축. 크기 증가 추이를 last_run.json·Release에서 확인 |

## 보안 원칙

- 인증키는 서버 측(Actions)에서만 사용한다. 브라우저 요청·프론트엔드 코드에 넣지 않는다.
- 수집기는 요청 URL을 출력하지 않고, 오류 문자열에서 인증키를 가린다.
