# M1 실제 착수 설계안 (최신 정리본)

## 0. 문서 목적

이 문서는 새 채팅에서 레포 코드를 다시 올렸을 때, **M1이 어떤 범위였고 어떤 구조를 이미 채택했는지** 빠르게 복구하기 위한 최신 정리본이다.  
원문 설계안은 유지하되, 지금 시점에서 중요한 변경점 두 가지를 반영한다.

1. M1은 이미 **완료**된 마일스톤이다.  
2. 레포 구조는 M1 기준 초안이지만, 이후 M3에서 **asset 계층**이 상위 개념으로 추가되었다.

---

## 1. M1의 목적

M1의 목적은 ChassisClaw를 “설명 문서”에서 “실행 가능한 골격”으로 바꾸는 것이었다.

즉 다음을 확보하는 단계였다.

- 프로젝트 상태 생성/조회
- run_auto 진입점
- 질문/답변/승인 반영
- validation / retry / replan 최소 루프
- skill registry
- 대표 skill stub 실행

---

## 2. M1 기준 레포 구조 요약

M1에서 목표로 한 최상위 구조는 아래다.

```text
chassisclaw/
├─ core/
├─ subagent/
├─ engine/
├─ bootstrap/
├─ skills/
├─ playbooks/
├─ org_profiles/
├─ audit/
├─ evidence/
└─ artifacts/
```

핵심 원칙:

- `core/`는 권위 있는 컨트롤 플레인
- `subagent/`는 대상 시스템의 실행면
- `engine/`는 선택적 실행 엔진
- `bootstrap/`는 초기 온보딩 전용

---

## 3. M1에서 고정된 핵심 모델

### 3.1 Project

프로젝트 상태의 기준점.

포함 내용:

- 사용자 요청
- 현재 상태
- stage
- `plan_ir`
- answers / approvals
- artifacts / evidence index

### 3.2 Playbook IR

자연어 목표를 실행 가능한 중간표현으로 바꾸는 구조.

최소 필드:

- `goal`
- `context`
- `constraints`
- `unknowns`
- `probes`
- `decisions`
- `plan`
- `validate`
- `errors`
- `fixes`
- `replans`
- `iterations`

### 3.3 Action IR

LLM이 실행 지시를 내릴 때 허용되는 최소 형식.

- `actions`
- `resolved_inputs`
- `question`
- `approval_request`

### 3.4 Tool Result

SubAgent 또는 실행 엔진이 돌려주는 결과 표준.

- `exit_code`
- `stdout`
- `stderr`
- `evidence_refs`
- `changed_files`
- `started_at`
- `ended_at`
- `resource_hints`

---

## 4. M1에서 확보해야 했던 API

### Core API

- `GET /health`
- `POST /projects`
- `GET /projects/{project_id}`
- `POST /projects/{project_id}/run_auto`
- `POST /projects/{project_id}/answer`
- `POST /projects/{project_id}/approve`
- `POST /targets`
- `GET /targets`
- `POST /llm/connections`
- `POST /llm/roles`
- `GET /artifacts/{artifact_id}`

### SubAgent API

- `GET /health`
- `GET /capabilities`
- `POST /a2a/run_script`
- `POST /a2a/push_file`
- `GET /a2a/pull_file`

### Engine API

- `GET /health`
- `POST /tasks/run`

---

## 5. M1의 실제 구현 우선순위

### 단계 1. 레포 경계 정리

- core / subagent / engine / bootstrap / skills 디렉터리 확정
- 백업성 web 코드 분리
- health endpoint만 먼저 살리기

### 단계 2. Core 모델 뼈대

- project / target / playbook_ir / action_ir / resolution / tool_result
- json store / project store / audit store / evidence store

### 단계 3. SubAgent 표준화

- `/health`
- `/a2a/run_script`
- `/capabilities`
- `/a2a/push_file`
- `/a2a/pull_file`

### 단계 4. 역할 기반 LLM registry

- connection 등록
- role binding
- master role lookup

### 단계 5. run_auto 뼈대

- planner_service 호출
- plan_ir 초기화
- target / answers / org_profile merge

### 단계 6. Probe Loop v0

- unknown 추출
- probe 생성
- SubAgent 실행
- evidence 저장
- LLM 재판단
- 질문 축소

### 단계 7. 질문/승인 루프

- answer 저장
- approve 저장
- 재실행 시 state merge

### 단계 8. Validate / Replan 최소 구현

- 목표 기반 validate rule
- fail 시 replan 진입
- 일부 실패 1회 retry

### 단계 9. 대표 Skill 등록

- `ops.onboard.two_node`

---

## 6. M1의 실제 완료 결과

M1은 아래까지 확보된 것으로 본다.

- `projects / targets / answers / approvals / run_auto` API 구성
- project state 저장/조회
- `plan_ir` 기반 상태 관리
- `resolved_inputs` merge
- 질문 후 재실행 가능
- `ValidationService` 도입
- retry / replan 최소 루프
- generic project 초기 상태 정리
- `skills/` registry 구현
- 대표 skill `ops.onboard.two_node` 등록
- `run_stub`, `execute_stub` 기본 골격 구현
- onboarding summary artifact 저장

즉,

> **M1은 “실행 가능한 코어 골격” 확보 단계로 완료되었다.**

---

## 7. M1의 한계

- 실제 install/patch/config apply는 아직 stub 수준
- playbook/skill 선택은 rule/stub 중심
- probe 일반화는 아직 약함
- 멀티 타겟은 테스트용 구조가 많음
- LangGraph 노드 분해는 아직 부분적
- org profile / experience는 본격 도입 전

---

## 8. 현재 시점에서 M1 문서를 읽을 때 주의할 점

이 문서는 M1 당시 기준이므로, 새 채팅에서는 아래 보정해서 해석해야 한다.

### 8.1 target이 최상위 기준은 아니다

현재는 `asset`이 추가되었기 때문에,

- 등록 기준: asset
- 실행 기준: target

으로 해석해야 한다.

### 8.2 대표 skill의 의미가 바뀌었다

`ops.onboard.two_node`는 원래 target 중심 stub로 시작했지만, 현재 기준으로는 **asset onboarding + target resolution skill**로 재구성 중이다.

### 8.3 local-agent seed는 임시 테스트 구조다

새 채팅에서는 가능하면 원격 VM 2대를 기준으로 보는 것이 맞다.

---

## 9. 새 채팅에서 바로 이어갈 때의 해석

새 채팅에서 이 문서를 참고할 때는 아래처럼 이해하면 된다.

- M1은 끝났다.
- core/subagent/engine/bootstrap 구조는 유지한다.
- 현재는 M2까지 구현 경험이 반영된 상태다.
- 다음 실제 개발은 M3의 asset 중심 리팩토링을 기준으로 간다.
