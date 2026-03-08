좋아. 그럼 바로 **Asset 반영 기준으로 ChassisClaw 핵심 모델을 재정의**해줄게.

# ChassisClaw 핵심 개념 재정의

## 1. Asset

ChassisClaw가 관리하는 자산의 기본 단위다.
서버, VM, 컨테이너 호스트, 네트워크 장비, 서비스 인스턴스처럼 “관리 대상 그 자체”를 뜻한다.

Asset의 역할:

* 자산 식별
* 접속/통신 정보 보관
* 현재 상태 보관
* capability 보관
* 어떤 agent가 붙어 있는지 보관
* 실행 이력과 experience의 기준점 역할

예:

* `asset_vm_192_168_208_143`
* `asset_vm_192_168_208_144`

---

## 2. Agent

Asset 위에서 실제 명령 실행과 상태 확인을 담당하는 실행 주체다.
현재는 주로 **subagent**가 agent 역할을 한다.

Agent의 역할:

* `/health`
* `/capabilities`
* 명령 실행
* 파일 배포
* evidence 수집
* 실행 결과 반환

중요한 점:

* agent는 asset에 종속된다
* asset이 더 상위 개념이고, agent는 그 자산 위의 실행 인터페이스다

즉,

* Asset = 관리 대상
* Agent = 실행 인터페이스

---

## 3. Target

Target은 고정 자산 DB 엔터티가 아니라, **특정 작업 시점에 선택된 실행 대상**이다.

예:

* “143번 VM에 nginx 설치”

  * asset = `asset_vm_192_168_208_143`
  * target = 현재 작업의 실행 대상

* “lab 태그 달린 노드 2대에 설치”

  * asset 후보 여러 개
  * target은 이번 run에서 resolve된 2개

즉 target은:

* 영구 저장 중심 개념이 아니라
* run/plan 안에서 해석되는 실행 단위다

---

## 4. Tool

실제 액션을 수행하는 최소 실행 단위다.

예:

* shell_exec
* http_probe
* file_write
* apt_install
* service_restart

Tool은 “어떻게 실행할 것인가”를 담당한다.

---

## 5. Playbook

Tool들을 절차적으로 묶은 작업 템플릿이다.

예:

* subagent bootstrap
* nginx install
* docker install
* log collect
* system audit

Playbook은 “무슨 순서로 할 것인가”를 담당한다.

---

## 6. Skill

사용자 자연어 요청을 받아,

* 어떤 asset을 찾을지
* 어떤 target으로 resolve할지
* 어떤 playbook/tool을 사용할지
* 어떤 승인/질의가 필요한지

를 결정하는 오케스트레이션 계층이다.

Skill은 “무엇을 왜 실행할 것인가”를 담당한다.

---

## 7. Experience

실행 결과와 실패/성공 패턴, remediation, 승인 이력 등을 축적한 운영 경험층이다.

예:

* 특정 asset 유형에서 bootstrap이 잘 되는 방식
* 특정 capability 부족 시 대체 절차
* 특정 playbook 실패 후 성공한 remediation 패턴

Experience는 “다음번엔 더 잘하게 만드는 기억”이다.

---

# 개념 간 관계

정리하면 이렇게 된다.

* **Asset**: 관리 대상
* **Agent**: asset 위에서 실행 담당
* **Target**: 특정 작업에서 선택된 asset의 실행 역할
* **Tool**: 실제 액션
* **Playbook**: tool 절차 묶음
* **Skill**: 요청 해석 + 계획/실행 오케스트레이션
* **Experience**: 결과 축적/재사용

관계 흐름은 이렇게 보면 된다.

**사용자 요청 → Skill → Asset 탐색 → Target resolve → Playbook 선택 → Tool 실행 → Experience 축적**

---

# ChassisClaw 운영 흐름 재정의

## A. 자산 온보딩 단계

1. 원격 시스템 정보 입력
2. subagent 설치 또는 연결
3. `/health`, `/capabilities` 확인
4. asset registry에 등록
5. asset-agent 매핑 저장

이 단계의 산출물은 **target이 아니라 asset**이다.

---

## B. 작업 실행 단계

1. 사용자 요청 입력
2. skill이 적절한 asset 탐색
3. 실행 가능한 asset을 target으로 resolve
4. playbook/tool 계획
5. approval/clarification 처리
6. 실행
7. evidence 저장
8. experience 축적

---

# 왜 이 구조가 중요한가

지금까지 꼬였던 핵심 원인은
**같은 subagent를 서로 다른 target처럼 취급한 것**이다.

하지만 asset 개념을 넣으면 문제를 정확히 분리할 수 있다.

* 같은 base_url이면 사실 같은 asset/agent일 가능성이 높다
* 서로 다른 asset이면 각자 고유한 agent identity가 나와야 한다
* target mismatch는 실행 단계 문제가 아니라 asset-agent 정합성 문제다

즉, 이제는
`target_id 불일치`가 아니라
`asset-agent identity mismatch`로 해석해야 한다.

---

# 데이터 모델 추천

## Asset 예시

```json
{
  "asset_id": "asset_vm_192_168_208_143",
  "asset_type": "vm",
  "display_name": "remote-vm-143",
  "hostname": "vm143",
  "ip_addresses": ["192.168.208.143"],
  "agent": {
    "agent_id": "subagent-143",
    "base_url": "http://192.168.208.143:55123",
    "connected": true,
    "last_seen": "2026-03-08T12:00:00Z"
  },
  "capabilities": {
    "sudo": true,
    "systemctl": true,
    "docker": false,
    "package_manager": "apt"
  },
  "labels": ["vm", "lab"],
  "state": "online"
}
```

## Target 예시

```json
{
  "target_id": "run_20260308_node_a",
  "asset_id": "asset_vm_192_168_208_143",
  "resolved_agent_id": "subagent-143",
  "role": "node_a"
}
```

---

# Skill 설계도 같이 바뀌어야 함

기존 `ops.onboard.two_node`는 이름은 onboarding인데 실제로는 target 기준으로 너무 빨리 들어가 있었다.

이제는 아래처럼 바뀌어야 한다.

## 새 흐름

1. 입력: node_a 주소, node_b 주소
2. 각 주소에 bootstrap 시도
3. subagent 연결 확인
4. asset 등록/갱신
5. agent identity 확인
6. 두 asset을 node_a / node_b target으로 resolve
7. onboarding summary 생성

즉 이 skill은 본질적으로:

**asset onboarding + target resolution skill**

이 되어야 한다.

---

# 네 현재 환경에 바로 적용하면

네가 말한 원격 VM 2대가 이미 있으니 이제 더미 `local-agent-1`, `local-agent-2` 방식은 버려야 한다.

대신 이렇게 가면 된다.

## 자산

* `asset_vm_192_168_208_143`
* `asset_vm_192_168_208_144`

## 각 VM에서 해야 할 것

* subagent 설치
* agent id 고유화
* `/health`에서 자기 고유 identity 반환

## manager가 해야 할 것

* 이 둘을 asset registry에 등록
* 두 asset을 onboarding skill 입력으로 사용
* 실행 시 target으로 resolve

---

# 마일스톤 관점에서 보면

## M3의 진짜 완료조건

M3는 “로컬 가짜 2노드 흉내”가 아니라 아래가 되어야 더 자연스럽다.

* asset registry 존재
* remote subagent bootstrap 가능
* asset-agent identity 검증 가능
* skill이 asset을 기반으로 target resolve 가능
* 2개의 서로 다른 VM에 대해 onboarding stub이 성공

지금 상태는 일부 로직은 있지만, **개념 모델은 아직 target 중심 잔재가 남아 있음**이다.

즉 완전한 의미의 M3 완료는 아직 아니다.

---

# 다음 작업 우선순위

## 1순위

`target_store`를 `asset_registry` 중심으로 재정의

## 2순위

원격 2대 VM에 실제 subagent 설치

## 3순위

`/health`의 `agent_id`가 자산별로 고유하게 나오게 구성

## 4순위

`ops.onboard.two_node` 입력을 asset 기준으로 전환

## 5순위

plan/run에서는 target을 동적으로 resolve

---

# 문서용 정의문

이 문장은 바로 계획서/README에 넣어도 된다.

> ChassisClaw는 관리 대상 시스템을 asset 단위로 등록하고, 실제 작업 요청 시점에 asset을 target으로 해석하여 실행하는 자산 중심 오케스트레이션 구조를 채택한다. 원격 시스템에 subagent가 설치되어 연결되면 해당 시스템은 asset registry에 등록되며, 이후 skill은 asset의 상태와 capability를 바탕으로 적절한 target을 resolve하고 playbook 및 tool을 통해 작업을 수행한다.

---

좋아. 그럼 **Asset 반영 기준으로 M3를 다시 정리**해줄게.

# M3 재정의

기존 M3를 “가짜 2노드 target 테스트”가 아니라 아래처럼 잡는 게 맞다.

**M3 목표:**
원격 시스템에 subagent를 실제로 설치해 asset으로 등록하고, 그 asset을 기반으로 skill이 target을 resolve하여 onboarding 흐름을 수행할 수 있게 만든다.

즉 M3는 이제 아래 4개가 핵심이다.

1. **Remote SubAgent Bootstrap**
2. **Asset Registry**
3. **Asset → Target Resolve**
4. **Two-node Onboarding Skill Stub**

---

# M3 완료조건

아래가 되면 M3 완료로 봐도 된다.

* 원격 VM 2대에 각각 subagent가 올라감
* 각 subagent가 서로 다른 `agent_id`를 반환함
* manager가 두 원격 시스템을 **asset**으로 등록함
* `ops.onboard.two_node`가 asset 기준으로 입력을 받거나 내부에서 asset 조회 가능
* 실행 시 각 asset이 올바른 target으로 resolve됨
* identity mismatch 없이 summary가 정상 생성됨
* install / probe / summary artifact가 저장됨

---

# M3-1. Remote SubAgent Bootstrap

## 목표

원격 VM 두 대에 실제 subagent 설치 및 health/capabilities 응답 확보

## 해야 할 일

* subagent 설치 스크립트 정리
* `CHASSISCLAW_AGENT_ID`를 VM별로 다르게 부여
* `/health` 응답에 고유 `agent_id` 포함
* `/capabilities` 응답 정상화
* 부팅 후 자동 실행 방식 확정

  * systemd 가능하면 systemd
  * 아니면 nohup fallback

## TODO

* bootstrap shell script 분리
* install script에서 테스트용 `nonexistent_command_zzz` 완전 제거
* 설치 후 health check retry 유지
* stderr/stdout evidence 저장
* 원격 VM 2대에 직접 설치 테스트

## 산출물

* `subagent_install.sh`
* `subagent.service`
* install evidence logs

---

# M3-2. Asset Registry 도입

## 목표

관리 대상을 target이 아니라 asset로 먼저 등록하는 구조로 변경

## 해야 할 일

* 현재 `target_store` 역할 재검토
* asset 저장 모델 추가
* asset 필드 정의
* asset와 agent 정보를 함께 저장

## 최소 asset 스키마 예시

```json
{
  "asset_id": "asset_vm_192_168_208_143",
  "display_name": "vm-143",
  "asset_type": "vm",
  "connection": {
    "host": "192.168.208.143",
    "port": 55123,
    "base_url": "http://192.168.208.143:55123"
  },
  "agent": {
    "agent_id": "subagent-143",
    "last_seen": null,
    "status": "unknown"
  },
  "capabilities": {},
  "labels": ["lab"],
  "state": "registered"
}
```

## TODO

* `asset_store.py` 추가
* `data/state/assets/` 디렉토리 도입
* asset create/get/list/update 구현
* 최초 등록 시 probe 결과 반영
* last_seen, status, capabilities 갱신 루틴 추가

## 산출물

* `core/app/storage/asset_store.py`
* `data/state/assets/*.json`

---

# M3-3. Asset Identity Validation

## 목표

같은 subagent를 서로 다른 대상처럼 착각하는 문제 제거

## 해야 할 일

* probe 시 `requested_asset`와 `reported_agent_id` 비교
* mismatch를 target 문제가 아니라 asset-agent 정합성 문제로 처리
* 동일 `base_url` 중복 등록 방지 또는 경고

## TODO

* asset 등록 시 base_url uniqueness 검사
* 동일 base_url인데 다른 asset_id면 warning/block
* health 응답의 agent_id 기반 fingerprint 저장
* mismatch 시 `needs_clarification` 대신 asset registration error로 구분 가능하게 개선

## 산출물

* asset validation 로직
* identity mismatch 진단 메시지 개선

---

# M3-4. Target Resolve 계층 분리

## 목표

target을 저장 객체가 아니라 실행 시점 해석 결과로 바꾸기

## 해야 할 일

* skill 입력은 asset 또는 asset selector 기준
* 실행 직전에 resolved target 생성
* target은 run context 내부 객체로만 사용

## target 예시

```json
{
  "target_id": "run_target_node_a",
  "asset_id": "asset_vm_192_168_208_143",
  "resolved_agent_id": "subagent-143",
  "role": "node_a"
}
```

## TODO

* `_get_target()` 중심 코드 제거/축소
* `_resolve_target_from_asset()` 함수 추가
* skill inputs를 `node_a_asset_id`, `node_b_asset_id` 방식으로 변경
* summary에도 asset_id와 resolved_agent_id 둘 다 남기기

## 산출물

* resolve layer
* run context target structure

---

# M3-5. ops.onboard.two_node Skill 재구성

## 목표

실제 두 자산을 받아 onboarding stub을 수행

## 해야 할 일

* precheck: asset 존재 확인
* probe: 각 asset의 subagent health/capabilities 확인
* decision: 설치 필요 여부 판정
* install: 필요 시 bootstrap 실행
* report: summary 작성

단, 이제 핵심은:

* 입력은 asset
* 실행은 resolved target
* 결과는 asset 기준으로 요약

## TODO

* `check_targets_exist` → `check_assets_exist`로 의미 변경
* `target_input` → `asset_input` 변경
* `_probe_target()` → `_probe_asset()` 또는 `_probe_agent_for_asset()`
* summary에 `assets` 섹션 추가
* blockers에 `asset_identity_mismatch` 명시

## 산출물

* 수정된 skill executor
* 수정된 onboarding summary

---

# M3-6. Summary / Artifact 정리

## 목표

지금처럼 중복 append나 혼란스러운 summary를 줄이고 asset 관점으로 정리

## 해야 할 일

* artifact append 중복 제거
* install artifact / remediation artifact / summary artifact 정리
* summary 상태값 단순화

## 추천 상태

* `registered`
* `reachable`
* `approval_needed`
* `install_planned`
* `install_executed`
* `completed`
* `needs_clarification`
* `failed`

## TODO

* `summary["artifacts"].append(...)` 중복 제거
* execution_ok 와 failure_summary 일관성 확인
* identity mismatch가 있으면 install success여도 최종 완료 막기
* next_actions를 asset 관점으로 재작성

---

# M3-7. 실제 테스트 시나리오

## 시나리오 A: 정상 2노드 온보딩

* VM 143, VM 144 각각 subagent 정상 설치
* agent_id 각각 다름
* asset 등록
* onboarding 실행
* 결과: success

## 시나리오 B: 같은 base_url 잘못 등록

* 두 asset이 같은 base_url
* probe 결과 동일 agent_id
* 결과: identity mismatch / clarification

## 시나리오 C: 한쪽 설치 실패

* 한 VM에서 bootstrap 실패
* remediation plan 생성
* 결과: partial / needs_clarification

## 시나리오 D: capability 부족

* sudo/systemctl 없음
* manual bootstrap 또는 alternate flow 제시

---

# 지금 바로 현실적으로 해야 할 순서

## 1단계

원격 VM 2대의 실제 subagent 설치부터 한다.

네가 말한 방향대로 이게 맞다.
더 이상 `local-agent-1`, `local-agent-2` 같은 같은 base_url 장난감 상태로 오래 끌면 안 된다.

## 2단계

asset registry를 만든다.

## 3단계

현재 `ops.onboard.two_node`를 asset 기반으로 고친다.

## 4단계

identity mismatch를 target 문제가 아니라 asset registration 문제로 재분류한다.

---

# 아주 짧은 결론

지금까지의 문제는 코드 버그만이 아니라 **개념 모델 부재**였다.
`asset`을 올리면 구조가 정리된다.

앞으로는 이렇게 간다.

**원격 시스템 설치 → asset 등록 → skill이 asset 선택 → target resolve → 실행**

이게 ChassisClaw의 맞는 방향이다.

원하면 다음 답변에서 바로
**M3 구현 TODO를 파일 단위로 쪼개서**

* 어느 파일을 만들고
* 어느 함수명을 바꾸고
* 어떤 순서로 수정할지

코드 작업 지시서 형태로 적어주겠다.

