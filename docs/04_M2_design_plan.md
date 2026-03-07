# M2 설계 및 구현 계획 (Governed Master & Recovery Loop)

## 1. 목표
M2는 OpsClaw의 “업무 자동화”를 한 단계 올려
**승인된 마스터 조언을 실제 실행/검증으로 연결하는 닫힌 루프**를 완성한다.

---

## 2. 핵심 기능 설계

### 2.1 Master Provider 라우팅
- Provider: `ollama | openai | anthropic`
- 정책:
  - openai/anthropic는 **MasterGate APPROVED + TRANSFORMED prompt만 전송**
  - ollama는 내부망이므로 선택적(정책에 따라 승인 요구 가능)

### 2.2 MasterGate 정책 운영화(YAML)
- 탐지: PII/Secrets/Internal asset
- 결정: ALLOW/TRANSFORM/BLOCK
- 기록: prompt_hash, findings, redactions, actor, decision

### 2.3 ApplyFeedback “자동 실행”
- Master 응답에서 verification commands를 추출
- SubAgent로 실행
- 결과 evidence를 수집
- Validate 재수행

### 2.4 Recovery Loop(재시도/중지)
- 실패 분류(Error taxonomy)
- 자동 수정(Fix) 가능한 것만 수행
- Stop conditions:
  - 동일 실패 3회
  - 연결 실패 지속
  - 정책 위반
  - 승인 미획득

### 2.5 Approval Queue 강화
- 위험 작업은 자동 실행하지 않고 승인 필요
- 승인/거부 사유 기록
- UI에서 pending/approved/rejected 관리

### 2.6 Evidence Pack 확장(Approval 포함)
- `/approvals/{id}/evidence.zip`
- 포함:
  - 마스터게이트 transformed prompt
  - 승인 기록
  - master reply
  - apply_feedback 실행 결과 evidence
  - audit timeline

---

## 3. 구현 계획(작업 단위)

### Step 1) Master provider 실호출 안정화
- env 기반 설정 검증(키/URL)
- 실패 시 UI에 “설정 필요” 표시(401/connection refused 노이즈 제거)

### Step 2) ApplyFeedback → Validate 자동 재실행
- apply_feedback 후 workflow validate 노드 재호출 또는 별도 validate 엔드포인트

### Step 3) Approval evidence.zip 구현
- approval 객체 기반으로 evidence_refs 수집
- audit 필터링 + mastergate 결과 포함

### Step 4) 정책 프로파일(조직별)
- profile별 allow/deny/transform 규칙 운영

---

## 4. 완료 기준
- 외부 Master 호출은 항상 MasterGate 통과 기록을 남김
- ApplyFeedback 실행 결과가 evidence로 남고 zip에 포함됨
- 실패 시 자동 재시도/중지조건이 동작
- 승인 큐에서 사람 개입 지점이 명확함