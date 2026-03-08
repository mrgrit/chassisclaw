좋다. 그럼 **M1 완료 보고 + 다음 마일스톤 TODO**로 정리한다.

# M1 완료 보고

## 1. 이번 마일스톤에서 완성한 것

이번 M1에서는 ChassisClaw의 핵심 뼈대를 세웠다.
단순히 API 몇 개 만든 수준이 아니라, **프로젝트 상태 저장 → 자동 실행 진입 → 질문/답변 반영 → validation/replan 최소 루프 → 대표 skill 선택/실행 stub**까지 이어지는 최소 작동 골격을 확보했다.

핵심 완료 항목은 아래와 같다.

### Core 기본 흐름

* `projects`, `targets`, `answers`, `approvals`, `run_auto` API 구성
* 프로젝트 상태를 JSON store에 저장/조회
* audit/evidence 저장 구조 확보
* `run_auto`로 프로젝트 실행 진입 가능

### State merge / resolve 루프

* `answers`, `approvals`, `resolved_inputs`를 `plan_ir`에 merge
* `resolved_inputs`가 생기면 `inputs`, `input_rationales`, `evidence_map` 반영
* 질문 후 재실행 시 이전 상태를 이어받아 진행 가능
* `unknowns` 감소 및 종료 처리 구현

### Validation / Retry / Replan 최소 루프

* `ValidationService` 도입
* `unknowns_remaining`, `last_action_failed`, `no_action_taken`, `passed` 구분
* retryable failure 판정
* 1회 retry 실행
* retry 실패 시 `replan` 전이
* `needs_clarification / needs_approval / failed / resolved` 상태 분기 정리

### Generic project 초기 상태 정리

* 프로젝트 생성 시 기본 `plan_ir`를 generic 구조로 변경
* 특정 시나리오용 `iface_in`, `iface_out` 기본 unknown 제거
* skill 프로젝트와 probe 프로젝트가 서로 상태를 오염시키지 않게 정리

### Skill Registry

* `skills/` 디렉터리에서 `skill.json`, `plan.template.json` 읽는 registry 구현
* `/skills`, `/skills/{id}`, `/skills/{id}/plan_template` API 구현
* 대표 skill을 core가 읽을 수 있게 연결

### 대표 Skill: `ops.onboard.two_node`

* skill manifest 작성
* input schema 작성
* plan template 작성
* README 작성
* `run_stub` 구현

  * required input 검증
  * target existence precheck
  * project에 selected skill 및 plan 주입
* `execute_stub` 구현

  * precheck job 실행
  * node A / node B probe stub 실행
  * decision stub 실행
  * onboarding summary report artifact 생성

### Report / Decision 흐름

* capabilities / health 결과를 기반으로

  * `already_present`
  * `installable_with_approval`
  * `manual_bootstrap_needed`
    판단 구조 확보
* `onboarding_summary.json` artifact 생성
* summary에 blockers / next_actions / overall_status 포함

---

## 2. 현재 상태를 한 줄로 정리하면

현재 ChassisClaw는
**“자연어 요청을 받은 뒤 프로젝트 상태를 만들고, 최소 probe/resolve/validate/replan 루프를 돌릴 수 있으며, 대표 skill 하나를 선택해 precheck → probe → decision → report까지 실행할 수 있는 M1 골격”** 이다.

즉 아직 완성형 자동화 플랫폼은 아니지만, 이제부터는 뼈대를 다시 뜯지 않고 기능을 얹어 갈 수 있는 상태다.

---

## 3. 아직 남아 있는 한계

M1은 뼈대이기 때문에 아래는 의도적으로 남아 있다.

### 실행 로직 한계

* 실제 install/patch/config apply 같은 본 실행 job은 아직 stub 수준
* `decision` 결과가 실제 `install_subagent` 액션으로 이어지지 않음
* playbook/skill 선택은 아직 rule/stub 수준

### Probe 한계

* probe 명령/파서는 환경마다 다를 수 있는데 아직 일반화가 약함
* 명령 부재, 도구 부재, 패키지 미설치 환경에 대한 적응형 처리 미구현
* 현재는 stderr/stdout을 “실패 사실”로만 일부 활용

### 멀티 타겟 한계

* 현재 테스트에서는 `local-agent-1`, `local-agent-2`가 같은 subagent endpoint를 참조
* 실제 분산 노드/원격 타겟 분리는 아직 미구현

### 구조 한계

* `run_auto`와 skill runner 흐름이 아직 완전히 하나의 상태기계로 통합되진 않음
* LangGraph 노드 수준 분해는 아직 안 들어감
* organization profile / experience / policy 계층은 아직 본격 도입 전

---

# 다음 마일스톤 TODO

## M2 목표

**“stub에서 실제 실행형 skill로 넘어가기”**

---

## M2-1. Approval 이후 실행 분기 연결

* `decision` 결과가 `approval_request`로 이어지게 하기
* `/approve` 이후 `install_subagent` 또는 `skip_install` 분기 실행
* 승인 여부가 실제 job 흐름에 반영되도록 연결

## M2-2. Install job stub

* `install_subagent` job 타입 추가
* package manager hint 기반으로 bootstrap script 초안 생성
* 설치 전 조건 확인
* 설치 시도 결과를 `job_results`와 evidence에 저장

## M2-3. Probe/Execution contract 일반화

* probe 결과를 특정 인터페이스 하드코딩 없이 observation contract로 정리
* stdout/stderr/log 기반 실패 유형 분류 강화
* `command not found`, `permission denied`, `timeout`, `network unreachable` 등을 구조화

## M2-4. Tool/Dependency 부족 대응 설계

* 실행 중 필요한 명령이 없을 때

  * 질문
  * 설치 승인 요청
  * 대체 도구 사용
  * 직접 구현
    중 하나를 선택하도록 구조 설계
* 이건 향후 LLM planner가 직접 판단하게 될 핵심 경로

## M2-5. Skill Runner 확장

* `execute_stub`를 step-by-step 실행기로 발전
* job별 `pending / running / succeeded / failed / skipped` 상태 부여
* summary를 job 결과 기반으로 자동 갱신

## M2-6. Target 모델 강화

* 동일 endpoint를 여러 target이 가리키는 현재 테스트 구조에서 벗어나
* 실제 노드별 고유 base_url / transport / auth 정보 모델링
* health/capabilities 결과에 target identity 일관성 검사 추가

## M2-7. Evidence / Artifact 정리

* 현재 artifact는 summary 중심
* 다음 단계에서는

  * probe result artifact
  * install plan artifact
  * bootstrap script artifact
  * final execution report
    로 확장

## M2-8. 상태기계 정리

* `created → planned → resolve → execute → validate → report → completed`
  같은 흐름으로 정리
* 현재 `run_auto`와 skill runner의 상태 전이 규칙을 공통화

---

# 바로 다음 추천 작업

다음으로 가장 자연스러운 건 이거다.

**M2-1: decision 결과를 approval → install job stub로 연결**

이걸 하면 시스템이

* 보고만 하는 골격
  에서
* 실제 실행을 준비하는 골격
  으로 한 단계 올라간다.
