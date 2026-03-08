맞다. **Tool이 빠지면 ChassisClaw의 핵심이 빠진다.**

ChassisClaw의 본질은 Playbook만 관리하는 시스템이 아니라, **Agent가 Tool을 사용해 실제 환경을 바꾸고, 그 결과(stdout/stderr/artifact/evidence)를 다시 읽어 다음 작업을 계획하는 실행 루프 시스템**이다. 업로드 문서도 Tool을 “시스템 내부 명령어와 즉시 생성한 쉘 스크립트, GitHub 등에서 다운로드해 설치·실행하는 OSS, 즉 지금 이 환경에서 실제로 실행 가능한 단위”로 정의하고 있다.  또 실행 표준 사이클 역시 `Plan → Probe → Resolve → Execute → Validate → Replan → Report`이며, Execute 단계에서 **스크립트/Tool/OSS를 실행**한다고 명시한다. 

그래서 확정 계획서는 **Playbook + Skill + Experience + 조직 프로파일**이 아니라,

# **Tool + Skill + Playbook + Experience + 조직 프로파일**

으로 다시 고정하는 게 맞다. Tool은 최하위 보조 개념이 아니라, **에이전트가 현실 세계와 접촉하는 핵심 실행면**이다. `shell`, `http`, `file`, `browser`, `OSS CLI`가 모두 Tool 범주이며, Skill은 그 Tool 사용을 통제된 계약으로 감싼 재사용 단위다. 

아래를 **수정 반영된 ChassisClaw 확정 계획서**로 보면 된다.

---

# ChassisClaw 확정 계획서 v2

## 1. 최종 제품 정의

ChassisClaw는 LangGraph와 A2A를 뼈대로 하는 **AI 에이전트 오케스트레이션 시스템**이다. 사용자는 자연어로 목표를 주고, **Master가 상위 판단과 검수를 담당**하며, **Manager가 상태기계와 정책, Playbook, 재계획을 운영**하고, **SubAgent가 대상 시스템에서 Tool을 사용해 실제 실행과 증빙 수집을 담당**한다. LangGraph는 실행 순서와 루프를 고정하고, A2A는 그 실행을 대상 시스템으로 분산한다. 

ChassisClaw의 가장 중요한 특징은 다음이다.

* Agent는 단순히 답변하지 않는다.
* Agent는 **Tool을 사용한다.**
* Tool은 OS 명령어, 실시간 생성 쉘스크립트, 다운로드해 설치한 OSS, 래퍼 CLI/API를 포함한다. 
* Tool 실행 결과(stdout/stderr, exit_code, artifacts, evidence_refs)는 다음 판단의 입력이 된다. 
* 따라서 ChassisClaw는 “대화형 시스템”이 아니라 **Tool-driven execution loop system**이다.

---

## 2. 핵심 철학

### 2.1 Tool-first Execution

ChassisClaw에서 실제 일은 Tool이 한다.
LLM은 Tool을 언제, 어디서, 어떤 순서로, 어떤 입력으로 사용할지 계획하고, 결과를 읽고 다음 행동을 정한다.

즉 구조는 다음과 같다.

**LLM이 계획한다 → Tool이 실행한다 → 결과가 evidence로 남는다 → LLM이 다시 판단한다**

이 방향은 문서의 “LLM이 probe와 action을 JSON으로 생성하고, SubAgent가 실행하고, stdout/stderr/evidence를 다시 LLM에 넣어 결정/재계획한다”는 구조와 일치한다.  

### 2.2 Evidence-first

모든 Tool 실행은 반드시 다음을 남겨야 한다.

* 실행 명령
* stdout/stderr
* exit code
* 생성 파일
* 사용한 OSS 버전/커밋/태그
* evidence refs

이건 Skill 계약 문서에도 명시돼 있다. 

### 2.3 Human-minimized but not human-eliminated

인터페이스 번호, 내부망 IP 범위, 로그 보관 기간 같은 조직별 운영 기준은 Tool probe만으로 최종 확정할 수 없으므로, 시스템은 필요한 경우 사용자에게 질문해야 한다. Experience는 결정을 보조할 뿐, 사용자 의도나 위험 승인이나 변할 수 있는 운영 기준을 대체하면 안 된다. 

### 2.4 YAML 중심이 아니라 IR 중심

YAML은 일부 metadata/contract 표현에 쓸 수 있으나, 최종 실행 표준은 IR(JSON 중간표현)이다. 자연어, YAML, LLM 출력은 모두 IR로 변환되어 실행된다. 문서도 YAML을 표준 프로토콜이 아니라 입력 포맷 중 하나로 격하해야 한다고 명시한다. 

---

## 3. 시스템의 최상위 구성요소

ChassisClaw는 다섯 층으로 구성된다.

## 3.1 Tool

실행 수단이다.

포함 범위:

* OS 명령어
* 실시간 생성 쉘 스크립트
* curl/http 호출
* 파일 조작
* GitHub 등에서 다운로드/설치하는 OSS
* 필요 시 자동 생성한 wrapper CLI/API

Tool은 “지금 이 환경에서 실제로 실행 가능한 단위”이며, ChassisClaw의 현실 접점이다.  

## 3.2 Skill

Tool 사용을 통제된 재사용 작업으로 감싼 단위다.

Skill은 다음을 가진다.

* 입력 스키마
* 출력 스키마
* 정책
* 검증 기준
* 증빙 규칙
* 필요 시 rollback

예:

* `sys.probe`
* `net.probe`
* `svc.probe`
* `pkg.install`
* `tool.discover`
* `tool.acquire`
* `tool.run`
* `tool.wrap` 

## 3.3 Playbook

여러 Skill과 Tool, 질문, 승인, 검증 단계를 묶는 **작업 전체의 실행 청사진**이다.

Playbook은 정적 YAML 파일 저장소가 아니라,

* 사용자 요청을 기반으로 LLM이 동적으로 초안 생성
* 실행 중 probe 결과로 수정
* 반복/안정 작업은 정식 Playbook/Skill로 승격

하는 구조로 간다.

## 3.4 Experience

과거 human 결정, 반복 성공 패턴, 조직 선호, 환경 지식을 저장한다.
단, 자동 결정을 대체하지 않고 후보 정렬과 질문 최소화에만 사용한다.  

## 3.5 Organization Profile

조직별 운영 기준을 저장한다.

예:

* 내부망/외부망 CIDR
* 인터페이스 naming 기준
* 로그 보관 기간
* 승인 체계
* 점검 가능 시간대
* 허용/금지 도구
* sudo/ssh/agent 정책

이 계층이 있어야 같은 조직에서 반복 질문이 줄어든다.

---

## 4. Agent 역할과 작동 방식

## 4.1 Master

Master는 최고 수준의 판단을 담당한다.

역할:

* 사용자 목표 해석
* 동적 Playbook 초안 생성
* Tool/Skill 후보 전략 수립
* 애매한 경우 최소 질문 생성
* 실패 시 재계획
* 완료 후 검수

중요:

* Master는 직접 실행하지 않는다.
* 실행 지시는 actions/decisions 형태로 만든다.

문서에서도 `master` role LLM이 probe/actions를 생성하고, 실행 결과를 다시 받아 판단하는 구조를 목표로 한다. 

## 4.2 Manager

Manager는 ChassisClaw의 컨트롤 플레인이다.

역할:

* LangGraph workflow 실행
* state / audit / evidence / artifact 저장
* Playbook IR 관리
* Tool/Skill 실행 orchestration
* A2A fan-out/fan-in
* policy/approval/ask/confirm 처리

즉 Manager는 “말을 잘하는 비서”가 아니라 **실행 상태기계 운영자**다.

## 4.3 SubAgent

SubAgent는 대상 시스템에서 실제 Tool 실행을 담당한다.

역할:

* `run_script`
* `push_file`
* `pull_file`
* capability probe
* stdout/stderr/artifact/evidence 수집

문서도 Manager가 만든 실행 단위를 SubAgent로 보내고, SubAgent가 스크립트/Tool/OSS 실행 결과를 evidence와 함께 보고한다고 정의한다. 

---

## 5. 표준 실행 사이클

ChassisClaw의 실행은 항상 아래 상태기계를 따른다.

### 5.1 Plan

사용자 목표를 분석해

* 목표
* 대상
* unknowns
* constraints/policy
* candidate tools/skills/playbooks
* validate 기준
  을 정리한다.

### 5.2 Probe

필요한 unknown을 최소 명령으로 확인한다.

예:

* `ip -o link show`
* `ip route`
* `systemctl status ...`
* `ss -lntp`
* `cat /etc/os-release`

probe도 Tool 실행이다. 문서도 missing input이 있으면 LLM이 probe 명령을 생성하고 SubAgent가 실행한다고 한다. 

### 5.3 Resolve

결정 방식은 네 가지다.

* AUTO: probe로 충분히 확정
* CONFIRM: 후보는 있지만 사용자 확인 필요
* ASK: 정책/의도 질문 필요
* APPROVAL: 위험 작업 승인 필요

문서의 표준 사이클도 AUTO/CONFIRM/ASK/APPROVAL을 Resolve 단계로 정의한다. 

### 5.4 Execute

Manager가 선택한 Playbook/Skill/Tool sequence를 SubAgent에 내려 실제 실행한다.

실행의 핵심은 Tool이다.

* shell script 실행
* OSS clone/download/install
* wrapper 생성 후 실행
* 여러 target에 병렬 실행
* 실패한 target만 재시도

### 5.5 Validate

동일 probe 또는 별도 validate rule로 성공 여부를 판정한다.

예:

* 서비스 active 상태
* 포트 리슨 여부
* 파일 생성 여부
* 재스캔 결과
* heartbeat 확인

### 5.6 Replan

실패 시 stdout/stderr와 evidence를 근거로 원인 후보를 다시 잡고 다음 Tool 실행 계획을 세운다.

문서도 실패 후 LLM이 원인 파악용 probe를 생성하고 수정 action을 실행한 뒤 재시도해야 한다고 적고 있다. 

### 5.7 Report

실행 결과를 요약 보고서와 evidence pack으로 남긴다.

---

## 6. Tool Lifecycle을 정식 코어 기능으로 채택

ChassisClaw의 핵심 차별점 중 하나는, 기존 Tool이 없으면 Agent가 새 Tool을 도입할 수 있다는 점이다.

문서에서도 “없으면 찾고/clone하고/문서학습해서/목적에 맞게 실행”을 Tool Lifecycle Skill 체계로 표준화한다고 되어 있다. 
또 M4 방향 문서에서도 Tool Lifecycle Engine의 표준 단계를 다음처럼 정의한다. 

### Tool Lifecycle 표준 단계

1. Discover
   필요한 OSS 도구 후보를 웹/GitHub 등에서 찾는다.
2. Acquire
   clone/download 하고 버전을 고정한다.
3. Understand
   README, `--help`, 예제에서 사용법을 추출한다.
4. Probe
   dry-run/샘플 입력으로 실행 가능성을 확인한다.
5. Execute
   실제 목적 달성 명령을 실행한다.
6. Record
   사용법, 명령, 버전, 출력 포맷을 IR/evidence에 저장한다.

즉 ChassisClaw는 “내장 도구만 쓰는 시스템”이 아니라, **필요 시 OSS를 스스로 도입해 Tool 체계에 편입하는 시스템**이다. 

---

## 7. Action IR v1

LLM이 Tool을 실제로 지휘하려면 출력 형식이 고정되어야 한다. 문서도 LLM이 JSON 형태의 actions/resolved_inputs/question을 생성해야 한다고 정리한다. 

Action IR v1은 아래 4종을 기본으로 한다.

### 7.1 actions

실행할 Tool 명령

예:

* `shell`
* `http`
* `file_op`
* `oss_install`
* `wrapper_gen`

기본 필드:

* id
* type
* target_id
* timeout_s
* script or params
* expected_artifacts

### 7.2 resolved_inputs

probe 결과 기반으로 확정된 값

예:

* `iface_in`
* `iface_out`
* `config_path`

### 7.3 question

사용자에게 물어야 할 최소 질문

예:

* 내부망 CIDR 범위
* 로그 보관기간
* 운영중 재기동 허용 여부

### 7.4 approval_request

고위험 실행 승인 요청

예:

* 방화벽 룰 적용
* 서비스 재기동
* 패키지 업그레이드
* 계정/권한 변경

---

## 8. 저장해야 할 핵심 데이터

### 8.1 Plan IR

* goal
* context
* constraints/policy
* unknowns
* candidate tools/skills/playbooks
* target set

### 8.2 Run IR

* chosen actions
* execution order
* action results
* resolved inputs
* questions/approvals
* replans

### 8.3 Evidence Index

* stdout/stderr
* files
* logs
* version info
* tool install records
* wrapper files

문서도 state에 `plan_ir`, `run_ir`, `evidence_index`를 저장해야 한다고 명시한다. 

---

## 9. NanoClaw 통합 원칙

NanoClaw는 ChassisClaw의 정체성이 아니라 **선택 가능한 Engine 통합 옵션**이다.

원칙:

* Core에 NanoClaw 로직을 섞지 않는다.
* 통합 시 `engine/` 계층으로만 넣는다.
* Core는 `engine_client`로만 호출한다.

이건 기존 chassisclaw 계획 문서의 조건과 동일하다. 

즉 현재 확정 구조는:

* Core = 권위
* Tool execution = SubAgent 기본
* NanoClaw = 필요 시 보강 엔진

이다.

---

## 10. 대표 유스케이스 커버 전략

22개 유스케이스 전체는 하나의 만능 Playbook으로 처리하지 않는다.
문서도 “하나의 만능 스킬”이 아니라 도메인별 최소 번들 조합으로 가야 한다고 정리한다. 

커버 방식은 다음이다.

* 공통 Probe Skills

  * `sys.probe`
  * `svc.probe`
  * `net.probe`
  * `fs.probe`
* Tool Lifecycle Skills

  * `tool.discover`
  * `tool.acquire`
  * `tool.understand`
  * `tool.run`
  * `tool.wrap`
* 운영/보안/클라우드 번들

  * onboarding
  * health check
  * network diagnosis
  * security audit
  * remediation
  * reporting

각 유스케이스는
**공통 상태기계 + Tool 사용 + 도메인 Skill 번들 + 조직 프로파일**
조합으로 처리한다.

---

## 11. 주요 마일스톤

## M1. Tool-Centric Core 확립

목표는 ChassisClaw를 Playbook 중심 설명에서 Tool-driven execution system으로 확정하는 것이다.

TODO

* [ ] Tool 모델 정의
* [ ] Action IR v1 정의
* [ ] shell/http/file/oss_install action 타입 확정
* [ ] stdout/stderr/exit_code/artifacts/evidence 공통 포맷 정의
* [ ] audit 이벤트 표준화
* [ ] run 결과 JSON 표준화

완료조건

* Agent가 Tool을 JSON actions로 지시하고
* SubAgent가 실행하고
* 결과가 다음 루프 입력으로 돌아온다

## M2. Master-Manager-SubAgent Workflow 확립

TODO

* [ ] role-bound LLM registry
* [ ] Master prompt contract
* [ ] Manager workflow orchestration
* [ ] SubAgent execution/evidence contract
* [ ] `/projects/{id}/answer`
* [ ] `/projects/{id}/approve`

완료조건

* Master가 probe/action/question을 생성
* Manager가 상태기계를 운영
* SubAgent가 Tool을 실행

## M3. Probe Loop / Replan Loop 구현

TODO

* [ ] `probe_loop.py`
* [ ] max_iter
* [ ] stop condition
* [ ] failure routing
* [ ] resolved_inputs merge
* [ ] question/approval branching

완료조건

* missing input 자동 해결
* 실패 후 probe→fix→retry 가능
* 무한루프 없음

## M4. Tool Lifecycle Engine 구현

TODO

* [ ] discover
* [ ] acquire
* [ ] understand
* [ ] probe
* [ ] execute
* [ ] record
* [ ] tool version pinning
* [ ] OSS evidence capture
* [ ] wrapper generation

완료조건

* 신규 OSS 1개를 자동 도입→실행→증빙까지 완주 

## M5. Skill / Playbook System 구현

TODO

* [ ] skill manifest schema
* [ ] dynamic playbook draft
* [ ] promotion rules
* [ ] validation rules
* [ ] rollback hooks

완료조건

* 반복 작업이 Skill/Playbook으로 승격됨

## M6. Organization Profile / Experience 구현

TODO

* [ ] org policy schema
* [ ] profile loader
* [ ] experience lookup/update
* [ ] 질문 중복 방지
* [ ] policy vs fact 분리

완료조건

* 인터페이스/IP/로그보관기간 같은 조직 기준을 누적 관리

## M7. Evidence / Report 구현

TODO

* [ ] evidence pack zip
* [ ] report markdown/pdf
* [ ] tool install logs 포함
* [ ] version snapshot 포함
* [ ] target matrix report

완료조건

* 제출 가능한 증빙팩 생성

## M8. NanoClaw Engine Integration Gate

TODO

* [ ] engine API 정의
* [ ] TaskSpec / RunResult 정의
* [ ] engine_client 구현
* [ ] NanoClaw 통합 feasibility check
* [ ] core boundary 검증

완료조건

* Core 비침범 조건을 만족할 때만 통합 진행

---

## 12. 최종 한 줄 정의

**ChassisClaw는 Master-Manager-SubAgent 구조 위에서, Agent가 Tool(OS 명령어, 동적 쉘 스크립트, OSS 다운로드·설치·실행, wrapper 생성)을 사용하고 그 stdout/stderr/evidence를 다시 읽어 다음 계획을 세우는 LangGraph+A2A 기반 AI 에이전트 오케스트레이션 시스템이다.**