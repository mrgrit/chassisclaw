# M2 구현 상세 문서 (MasterGate 완성)

## 1. M2 목표
M2의 목표는 **MasterGate(외부/상용 LLM 호출 전 데이터 거버넌스 + 승인 워크플로우)**를 “실제로 굴러가는 운영 기능”으로 완성하는 것이다.

M2 완료 시점에서 MasterGate는 다음을 만족한다.

- 요청 생성 → 정책 판정(Allow/Transform/Block) → 승인(approve/reject) → 마스터 호출 → Apply+Validate(닫힌 루프) → 증빙팩 ZIP 생성/다운로드
- UI에서 운영자가 **필터/검색/정렬/created_at 확인/일괄 승인**을 수행 가능
- 모든 주요 이벤트가 audit.jsonl에 남음

---

## 2. 시스템 구성(실제 동작 기준)

### 2.1 컨테이너
- **web (80/tcp)**: Express + EJS UI
- **api (8000/tcp)**: FastAPI(워크플로우/승인/마스터 호출/증빙팩 생성)
- **subagent (55123/tcp)**: 명령 실행/증빙 수집 실행 노드
- **db (5432/tcp)**: Postgres(현재 단계에서 상태 저장은 파일 기반이지만, 향후 확장 기반)

### 2.2 저장소/파일 기반 스토어
- **State Store(파일)**
  - approvals: `/data/state/_approvals/{approval_id}.json`
  - (프로젝트/워크플로우 결과 등도 유사 구조로 축적)
- **Evidence Store(파일)**
  - `/data/evidence/*_run_stdout.log`
  - `/data/evidence/*_run_stderr.log`
- **Audit Store(JSONL)**
  - `/data/audit/audit.jsonl`
- **ZIP Evidence Pack**
  - API에서 동적으로 생성/다운로드 제공 (Approval 단위)

---

## 3. 데이터 모델(승인 단위 Approval)

### 3.1 Approval(요약 필드)
- `approval_id`: UUID
- `title`: 표시명
- `created_at`: 생성 시각(ISO)
- `decision_state`: `PENDING | APPROVED | REJECTED`
- `gate`: MasterGate 판정 결과
  - `decision`: `ALLOW | TRANSFORM | BLOCK`
  - `prompt_hash`: 전송 프롬프트 해시
  - `findings`: 탐지 항목(PII/secret/internal 등)
  - `redactions`: 마스킹 내역
  - `transformed_prompt`: 변환된 프롬프트(허용/변환 시)
- `final_prompt`: 최종 마스터 전송 프롬프트
- `master_provider`: `ollama | openai | anthropic | null`
- `master_reply`: 마스터 응답(원문/구조)
- `apply_feedback_runs[]`: Apply+Validate 실행 기록(명령/exit_code/evidence_refs 등)

### 3.2 created_at 정책
- Approval 생성 시 `created_at` 생성
- 과거 데이터는 파일 mtime 기반으로 보완 표시 가능(운영 편의)

---

## 4. API 엔드포인트(핵심)

### 4.1 상태/연동 확인
- `GET /health`
  - API 살아있는지 확인
- `GET /settings/status`
  - 모델/키 설정 상태 요약(최대한 “죽지 않게” best-effort)

### 4.2 Approval 조회/상세
- `GET /approvals`
  - approval 요약 리스트 반환(items[])
  - 포함: `approval_id`, `title`, `created_at`, `decision_state`, `gate.decision`, `master_provider`, `has_master_reply`, `has_apply_feedback_validate` 등
- `GET /approvals/{approval_id}`
  - 단일 approval 상세(JSON)

### 4.3 MasterGate Request 생성/승인
- `POST /mastergate/request`
  - 입력: title, draft_prompt, context_snippets, require_approval
  - 출력: approval 생성 결과(초기 상태 PENDING)
- `POST /approvals/{approval_id}/decide`
  - 입력: decision(approve|reject), actor, reason
  - 출력: updated approval

### 4.4 마스터 호출
- `POST /approvals/{approval_id}/ask_master`
  - 입력: provider(ollama/openai/anthropic)
  - 동작: final_prompt를 provider로 전송 후 master_reply 저장
  - 출력: 저장 결과/요약

### 4.5 Apply + Validate(닫힌 루프)
- `POST /approvals/{approval_id}/apply_feedback_and_validate`
  - 입력: actor, max_commands, timeout_s, stop_on_fail
  - 동작:
    - master_reply에서 검증/조치 커맨드 추출(실패 시 에러)
    - subagent 실행 → stdout/stderr evidence 저장
    - pass/fail 판정 및 결과 저장
  - 출력: pass/fail + failed_steps + evaluated_count

### 4.6 Evidence Pack
- `GET /approvals/{approval_id}/evidence.zip`
  - approval 단위 ZIP 다운로드
  - 포함 예시:
    - `approval.json`
    - `mastergate.json`
    - `master_prompt.txt`
    - `master_reply.json`
    - `apply_feedback_validate.json`
    - `audit_approval.jsonl`
    - `manifest.json`
    - `evidence/*.log`

### 4.7 (M2) 운영자 기능: Bulk Decide
- `POST /approvals/bulk_decide`
  - 입력:
    - `approval_ids[]`
    - `decision`: approve|reject
    - `actor`, `reason`
  - 동작:
    - 최대 200개
    - PENDING만 처리, 나머지는 skipped 처리
    - audit에 `MASTERGATE_BULK_DECISION` 기록
  - 출력: results[] + approved/rejected/skipped 카운트

---

## 5. Web UI(MasterGate) 구현 내용

### 5.1 MasterGate 메인 화면 구성
1) **Create MasterGate Request**
- title, draft_prompt, context_snippets 입력
- Submit → Approval 생성 결과 JSON 표시

2) **Approval Queue**
- 목록 항목: title + created_at + gate decision + decision_state
- **필터**: ALL/PENDING/APPROVED/REJECTED
- **정렬**: PENDING first / Newest / Oldest / Title
- **검색**: title/id 부분검색
- **PENDING count** 표시
- **ZIP quick link** 제공
- **체크박스 선택 + Select visible/Clear** 제공

3) **Selected Approval**
- ID/Status/Gate/Created 요약 카드
- Evidence ZIP 다운로드 버튼
- Apply+Validate 결과는 요약 카드 + 전체 JSON 접기(details)
- 큰 JSON은 기본 접기(대용량 렌더링 문제 방지)

### 5.2 Bulk Decide UI
- Approval Queue에서 체크박스 선택
- actor/reason 입력
- Approve selected / Reject selected 한 번에 처리
- 처리 후 자동 refresh

---

## 6. 운영/테스트 절차(실전 커맨드)

### 6.1 서비스 기동
```bash
sudo docker compose up -d --build
sudo docker compose ps
```

### 6.2 API 헬스
```bash
curl -sS http://localhost:8000/health
curl -sS http://localhost:8000/settings/status | python3 -m json.tool | head
```
### 6.3 요청 생성 → 승인 → 마스터 → Apply+Validate → ZIP

대표 흐름:

# create
```bash
AID=$(curl -sS -X POST http://localhost:8000/mastergate/request \
  -H 'content-type: application/json' \
  -d '{"title":"Ask Master","draft_prompt":"Give verification commands.","context_snippets":"","require_approval":true}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["approval_id"])')
```
# approve
```bash
curl -sS -X POST "http://localhost:8000/approvals/$AID/decide" \
  -H 'content-type: application/json' \
  -d '{"decision":"approve","actor":"admin","reason":"ok"}' | python3 -m json.tool | head
```
# ask master
```bash
curl -sS -X POST "http://localhost:8000/approvals/$AID/ask_master" \
  -H 'content-type: application/json' \
  -d '{"provider":"ollama"}' | head
```
# apply+validate
```bash
curl -sS -X POST "http://localhost:8000/approvals/$AID/apply_feedback_and_validate" \
  -H 'content-type: application/json' \
  -d '{"actor":"system","max_commands":5,"timeout_s":60,"stop_on_fail":true}' \
  | python3 -m json.tool | head -n 80
```
# evidence zip
```bash
curl -L -o "approval_${AID}.zip" "http://localhost:8000/approvals/$AID/evidence.zip"
unzip -l "approval_${AID}.zip" | head -n 60
```
### 6.4 Bulk Decide 테스트
```bash
curl -sS -X POST http://localhost:8000/approvals/bulk_decide \
  -H 'content-type: application/json' \
  -d '{"approval_ids":["<id1>","<id2>"],"decision":"approve","actor":"admin","reason":"bulk test"}' \
  | python3 -m json.tool | head -n 120

sudo docker compose exec api sh -lc 'tail -n 20 /data/audit/audit.jsonl'
```
## 7. M2에서 실제로 반영한 안정성 포인트

“한 줄 수정”도 서비스가 죽을 수 있으므로:

UI는 큰 JSON은 접기

/settings/status는 best-effort로 절대 죽지 않게 작성

실수로 main.py가 깨지면 api가 죽고 web이 연쇄적으로 죽으므로:

수정 후 curl /health + curl /settings/status + curl -I / 3종 체크를 표준으로