
---

```markdown
# M3 계획 상세 문서 (운영 고도화 + 플랫폼 확장)
- 현재 OpsClaw는 Postgres 컨테이너가 있으나, 승인 큐/상태는 /data/state 파일 스토어를 기준으로 동작한다.

## M3-1: Archive/Retention + 조회 옵션(운영 필수)

### 목표
- 승인 큐가 무한히 쌓이지 않도록 “정리/보관”을 제공
- 기존 UI 필터/검색/정렬 흐름은 유지하되, **아카이브 포함/아카이브만**을 지원
- 일정 기간 이후(정책 기반) 아카이브 항목을 purge(물리 삭제) 가능하게 함

### 구현 항목
1) **Approval Archive(소프트 아카이브)**
- approval JSON에 아래 필드 추가(하위호환):
  - `archived_at: string | null` (ISO8601)
  - `archived_by: string | null`
  - `archived_reason: string`
- 파일 이동은 하지 않음(안전/단순). 기존 저장 위치 유지:
  - `/data/state/_approvals/{id}.json`

2) **API**
- 리스트 조회:
  - `GET /approvals?include_archived=true|false&only_archived=true|false`
  - 기본값은 archived 제외
- 단건 조작:
  - `POST /approvals/{id}/archive` body: `{ actor, reason }`
  - `POST /approvals/{id}/restore` body: `{ actor, reason }`
- Retention(파일 기반 설정):
  - `GET /retention`
  - `POST /retention` body: `{ enabled?, approvals_purge_after_days? }`
  - `POST /retention/purge` body: `{ dry_run: true|false }`

3) **UI**
- Approval Queue 상단에 토글:
  - `include archived`
  - `only archived`
- 리스트 row에 `ARCHIVED` 배지 표시
- Selected Approval에 `Archive/Restore` 버튼(Actor/Reason 입력 포함)

4) **Audit 이벤트**
- `APPROVAL_ARCHIVE`
- `APPROVAL_RESTORE`
- `RETENTION_UPDATE`
- `RETENTION_PURGE`

### 완료 기준
- 운영자가 승인 큐를 archive/restore로 안전하게 정리 가능
- archived 기본 숨김 + 필요 시 포함/전용 조회 가능
- retention 정책 기반 purge(dry_run 포함) 및 audit 기록 가능

---

## M3-2: 권한/RBAC 최소 버전 + 감사 강화
### 목표
- “누가 승인했는지”가 명확하고, 승인 권한이 통제됨

### 구현 항목
1) 최소 Auth
- web에 간단한 관리자 토큰(환경변수)
- API에 admin 토큰 헤더 요구(선택)

2) RBAC 스키마(초기)
- roles: viewer / operator / approver / admin
- approve/reject/bulk_decide/bulk_archive는 approver 이상만 허용

3) 감사 로그 확장
- 모든 변경 이벤트에:
  - actor, ip, user_agent(optional), request_id
- 주요 레코드에 hash:
  - final_prompt hash, evidence pack manifest hash

### 완료 기준
- 승인 관련 행위가 최소한의 권한 제어를 통과
- 감사 로그로 “누가 무엇을” 추적 가능

---

## M3-3: Master 응답 포맷 강제 + 파서 안정화(품질 핵심)
### 목표
- “No verification commands found” 같은 불안정 제거
- 모델별(ollama/openai/anthropic) 응답 차이를 흡수

### 구현 항목
1) **응답 스키마 통일**
- 강제 JSON schema 예:
  - `{ "verification_commands": ["cmd1", ...], "notes": "...", "risk": "low|med|high" }`
- 모델 호출 시 system prompt에 schema를 강하게 요구
- 파서:
  - JSON 파싱 실패 시 재요청(재시도 정책)

2) **Sanitizer/Guardrails 강화**
- container-safe( sudo/systemctl 금지 등) 프로파일을 정책으로
- 위험 명령 denylist 강화 + 사유 반환

3) **Apply+Validate 전략 고도화**
- 커맨드 실행 전 “사전 검증”
  - 바이너리 존재 여부
  - docker.sock 존재 여부 등
- 실패 시:
  - 원인 분류(Error Taxonomy) + 다음 질문 자동 생성

### 완료 기준
- master_reply에서 커맨드 추출 성공률이 크게 상승
- 실패해도 “다음 행동”이 자동으로 제안됨

---

## M3-4: Workflow 표준화(프로젝트 타입/플레이북/RAG로 확장)
### 목표
- MasterGate는 “컴플라이언스 레이어”로 고정하고,
- OpsClaw 전체 워크플로우(프로젝트 기반)에 결합

### 구현 항목
1) Project 타입별 템플릿
- incident triage / patch cycle / deploy change 등

2) Playbook Template
- 성공한 플로우를 템플릿화(명령/검증/증빙 규격)

3) RAG Store 연계(초기)
- 내부 런북/ADR을 검색해 프롬프트에 주입
- “외부 마스터 호출 전” 로컬 지식으로 해결 우선

### 완료 기준
- 업무 유형별로 반복 가능한 자동화 패턴 확보
- “조직 운영 자동화 플랫폼”으로 확장 가능한 기반 완성

---

## 3. M3 우선순위(현실적인 순서)
1) **M3-1(Archive/Query)**: 큐 폭발 방지 + 성능/운영 필수
2) **M3-3(응답 포맷/파서 안정화)**: 품질/신뢰성 핵심
3) **M3-2(RBAC/감사)**: 배포/조직 도입 필수
4) **M3-4(플레이북/RAG/프로젝트 통합)**: 플랫폼 확장

---

## 4. M3 산출물(깃허브 기준)
- `docs/M3-PLAN.md` (이 문서)
- `docs/ARCHIVE_RETENTION.md` (M3-1 상세)
- `docs/RBAC_AUDIT.md` (M3-2 상세)
- `docs/MASTER_REPLY_SCHEMA.md` (M3-3 상세)
- `docs/PLAYBOOKS.md` (M3-4 상세)