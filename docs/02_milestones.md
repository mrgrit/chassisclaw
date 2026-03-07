# OpsClaw 마일스톤 구성(전체 설계)

## 마일스톤 목표
- M1: “Core Workflow + Evidence”로 플랫폼 뼈대 완성
- M2: “Governed Master + Recovery Loop”로 운영 자동화 수준 상승
- M3: “플러그인/도메인 확장 + 정책 운영화”로 제품화

---

## M1: Core Workflow + Evidence MVP
### 목표
- 워크플로우(상태기계) 기반의 표준 절차 실행
- SubAgent 분산 실행
- 상태/감사/증빙 저장 및 다운로드

### 필수 기능
- LangGraph 6노드 워크플로우
- Validate + Diagnose/Decide(최소)
- Evidence Pack ZIP
- Web UI에서 실행/다운로드

### 산출물
- `/projects/{id}/run_workflow`
- `/projects/{id}/evidence.zip`
- audit.jsonl + state.json 누적

---

## M2: Governed Master & Recovery Loop
### 목표
- MasterGate 승인 후 (OpenAI/Claude/Ollama) 선택 호출
- Master 조언을 실제 실행(ApplyFeedback)으로 연결
- 실패 시 자동 진단/수정/재시도까지 닫힌 루프

### 필수 기능
- Master provider 라우팅(ollama/openai/anthropic) 안정화
- MasterGate 정책 파일(YAML) 기반 운영
- ApplyFeedback 자동 실행 + 결과 검증 + 증빙팩 확장(approval 포함)
- Stop conditions / Retry policy 고도화
- “승인 필요 작업” 라우팅(Approval Queue 연동)

---

## M3: 플러그인/도메인 확장 + 운영 제품화
### 목표
- 업무 템플릿/스킬 플러그인
- RBAC/조직 사용자/권한
- Observability(메트릭/대시보드)
- 오프라인 번들/미러 배포 체계

### 기능 확장 예시
- ITSM 티켓 연동
- 자산 인벤토리 업데이트
- 클라우드/가상화 운영(Provisioning, Patch)
- 보안 도메인(규칙 배포/회귀 테스트) 플러그인

---

## 완료 기준(정량)
- 성공률/재시도/중지율
- 증빙팩 생성률
- 승인 대기 시간
- MasterGate block/transform 비율