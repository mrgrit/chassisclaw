# OpsClaw 개요 (Concept / Design / Examples)

## 1. 한 줄 정의
**OpsClaw는 LangGraph(상태기계) 기반 워크플로우 엔진 + A2A(SubAgent 분산 실행)를 결합해, IT 업무를 “계획→실행→검증→증빙→보고” 절차로 표준화/자동화하는 오케스트레이션 플랫폼이다.**

- 보안은 “도메인 중 하나”
- **MasterGate**는 “보안 기능”이 아니라 **업무용 데이터 거버넌스 레이어(외부 전송 통제)**

---

## 2. 사용자 관점(Operator / Manager)

### 2.1 OpsClaw가 해결하는 문제
업무 자동화가 실패하는 가장 흔한 이유는 “작동은 하는데 책임/증빙/재현이 없다”는 점이다.

OpsClaw는 다음을 기본값으로 제공한다.
- **절차 내장**: 단계(노드)·마일스톤·중지조건이 명시됨
- **재현성**: 상태(State)가 저장되어 “이미 확인한 것”을 반복하지 않음
- **감사/증빙**: Audit + Evidence Pack(증빙 ZIP)으로 결과를 제출할 수 있음
- **폐쇄망 우선**: SubAgent는 내부망에서 실행, 외부 모델은 선택적(정책 통과 시만)

### 2.2 사용 흐름(핵심 UX)
1) Project 생성  
2) Workflow 실행 (LangGraph)  
3) Pass/Fail 확인  
4) Evidence Pack 다운로드  
5) (필요 시) MasterGate 승인 후 외부/내부 Master 호출 → ApplyFeedback 실행

---

## 3. 개발자 관점(Architecture / Components)

## 3.1 구성 요소
- **Web Console**: 프로젝트 생성/워크플로우 실행/ZIP 다운로드 UI
- **Manager API (FastAPI)**: 워크플로우 오케스트레이션, 정책/승인, 상태 저장
- **SubAgent (FastAPI)**: 로컬 실행 노드 (명령 실행, evidence 파일 저장)
- **State Store**: 프로젝트 상태(JSON)
- **Evidence Store**: 실행 결과 로그/덤프 파일
- **Audit Store**: 감사 이벤트(JSONL)
- **(옵션) Master Providers**: Ollama / OpenAI / Anthropic

### 3.2 책임 분리(핵심 철학)
- **Manager**: 생각/계획/검증/기록(상태·감사·증빙 조직화)
- **SubAgent**: 실행/수집(현장 실행기, 분산 확장 가능)
- **Master**: 조언(선택적, 외부 호출 전 MasterGate 필수)

---

## 4. 워크플로우 설계(LangGraph)
OpsClaw의 업무는 “대화”가 아니라 **상태 기반 절차**다.

### 4.1 표준 6노드(기본)
- Intake → Plan → GenerateArtifacts → Dispatch → Collect → Validate

### 4.2 실패 대응(확장)
- Validate 실패 시 Diagnose → Decide → (Fix → Retry) or Stop

---

## 5. A2A(SubAgent) 실행 모델
- Manager가 `RUN_SCRIPT` 요청
- SubAgent가 실행 후 `RUN_RESULT` 반환
- 결과는 표준 포맷(ExitCode/Stdout/Stderr/EvidenceRefs)
- Evidence는 파일로 저장되고 Manager가 참조를 보관

---

## 6. MasterGate(데이터 거버넌스)
외부 모델 질의 시 반드시 수행:
- PII/Secrets/내부자산 탐지
- Transform(마스킹/요약) 또는 Block
- 승인 모드면 승인자 결정 기록
- 감사 로그에 전송 해시/규칙/승인 기록

---

## 7. 사용 예시(시나리오)

### 7.1 운영 점검(기본 워크플로우)
- Workflow 실행
- uname/uptime/df/ss 등 수집
- Validate(pass/fail)
- ZIP로 제출

### 7.2 장애 트리아지(확장)
- 오류 로그 일부(민감 제거)를 입력
- MasterGate 승인 → Master 조언
- ApplyFeedback으로 검증 커맨드 자동 실행
- 결과 evidence + audit로 리포트 생성

### 7.3 폐쇄망 운영
- SubAgent를 대상 서버/점프호스트에 배치
- 외부 Master 비활성화(또는 승인형)
- 모든 결과는 내부에 저장, ZIP로 내부 제출

---

## 8. 레포 구조(현재 MVP 기준)
- `api/` : Manager API + LangGraph workflow + MasterGate + Evidence Pack
- `subagent/` : 실행 노드
- `web/` : Console UI
- `/data` 볼륨 : state / evidence / audit

---

## 9. 핵심 산출물
- **Workflow run 기록**: 상태에 누적
- **Audit log**: 사건의 타임라인
- **Evidence Pack ZIP**: 제출 가능한 증빙팩