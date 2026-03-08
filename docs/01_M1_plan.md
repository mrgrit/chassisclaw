좋다. 아래를 **ChassisClaw 실제 착수용 설계안**으로 보면 된다.
이번에는 추상 설명이 아니라 **실제 레포 폴더 구조 + 모듈명 + API 명세 + 첫 마일스톤 구현 순서**까지 바로 개발 시작 가능한 수준으로 내린다.

문서 기준으로도 우선순위는 이미 정해져 있다. 먼저 **프로그램을 4~5개로 분리**하고, 그 다음 **Core↔Engine 계약(TaskSpec/RunResult)** 을 정의하며, 첫 대표 Skill은 **2노드 온보딩**으로 고정하는 것이 맞다. 
또 전체 코어는 **Master / Manager / SubAgent**, **LangGraph + A2A**, **Tool / Skill / Experience**, 그리고 `Plan → Probe → Resolve → Execute → Validate → Replan → Report` 표준 사이클 위에 서야 한다.   

---

# 1. 레포 최종 구조

레포 이름은 `chassisclaw/` 기준으로 잡는다.

```text
chassisclaw/
├─ README.md
├─ .env.example
├─ docker-compose.yml
├─ Makefile
├─ docs/
│  ├─ architecture/
│  │  ├─ 001_master_manager_subagent.md
│  │  ├─ 002_tool_skill_playbook_experience.md
│  │  ├─ 003_core_engine_boundary.md
│  │  └─ 004_org_profile_and_question_policy.md
│  ├─ api/
│  │  ├─ core_api.md
│  │  ├─ subagent_api.md
│  │  └─ engine_api.md
│  ├─ playbooks/
│  │  └─ playbook_ir_v1.md
│  └─ milestones/
│     ├─ M1_tool_centric_core.md
│     ├─ M2_probe_loop.md
│     └─ M3_onboarding_skill.md
│
├─ core/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ deps.py
│  │  ├─ api/
│  │  │  ├─ health.py
│  │  │  ├─ projects.py
│  │  │  ├─ targets.py
│  │  │  ├─ llm.py
│  │  │  ├─ run_auto.py
│  │  │  ├─ approvals.py
│  │  │  ├─ answers.py
│  │  │  ├─ artifacts.py
│  │  │  ├─ skills.py
│  │  │  ├─ playbooks.py
│  │  │  └─ org_profiles.py
│  │  ├─ models/
│  │  │  ├─ project.py
│  │  │  ├─ target.py
│  │  │  ├─ llm.py
│  │  │  ├─ audit.py
│  │  │  ├─ artifact.py
│  │  │  ├─ org_profile.py
│  │  │  ├─ skill.py
│  │  │  ├─ playbook_ir.py
│  │  │  ├─ action_ir.py
│  │  │  ├─ tool_result.py
│  │  │  ├─ resolution.py
│  │  │  └─ validation.py
│  │  ├─ services/
│  │  │  ├─ project_service.py
│  │  │  ├─ target_service.py
│  │  │  ├─ llm_registry.py
│  │  │  ├─ audit_service.py
│  │  │  ├─ evidence_service.py
│  │  │  ├─ artifact_service.py
│  │  │  ├─ org_profile_service.py
│  │  │  ├─ skill_registry.py
│  │  │  ├─ playbook_registry.py
│  │  │  ├─ planner_service.py
│  │  │  ├─ probe_loop_service.py
│  │  │  ├─ resolution_service.py
│  │  │  ├─ execution_service.py
│  │  │  ├─ validation_service.py
│  │  │  ├─ report_service.py
│  │  │  ├─ approval_service.py
│  │  │  ├─ answer_service.py
│  │  │  ├─ subagent_client.py
│  │  │  ├─ ssh_adapter.py
│  │  │  └─ engine_client.py
│  │  ├─ workflows/
│  │  │  ├─ graph.py
│  │  │  ├─ states.py
│  │  │  ├─ nodes/
│  │  │  │  ├─ plan_node.py
│  │  │  │  ├─ probe_node.py
│  │  │  │  ├─ resolve_node.py
│  │  │  │  ├─ execute_node.py
│  │  │  │  ├─ validate_node.py
│  │  │  │  ├─ replan_node.py
│  │  │  │  └─ report_node.py
│  │  ├─ storage/
│  │  │  ├─ paths.py
│  │  │  ├─ json_store.py
│  │  │  ├─ project_store.py
│  │  │  ├─ audit_store.py
│  │  │  ├─ artifact_store.py
│  │  │  ├─ evidence_store.py
│  │  │  ├─ skill_store.py
│  │  │  ├─ playbook_store.py
│  │  │  └─ org_profile_store.py
│  │  └─ prompts/
│  │     ├─ master_plan.txt
│  │     ├─ master_probe.txt
│  │     ├─ master_decide.txt
│  │     ├─ master_replan.txt
│  │     └─ master_review.txt
│  └─ tests/
│     ├─ test_health.py
│     ├─ test_projects.py
│     ├─ test_run_auto.py
│     └─ test_probe_loop.py
│
├─ subagent/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ api/
│  │  │  ├─ health.py
│  │  │  ├─ run_script.py
│  │  │  ├─ files.py
│  │  │  └─ capabilities.py
│  │  ├─ models/
│  │  │  ├─ run_script.py
│  │  │  ├─ file_transfer.py
│  │  │  ├─ capability.py
│  │  │  └─ tool_result.py
│  │  ├─ services/
│  │  │  ├─ runner.py
│  │  │  ├─ file_service.py
│  │  │  ├─ capability_service.py
│  │  │  └─ evidence_service.py
│  │  └─ storage/
│  │     ├─ paths.py
│  │     └─ evidence_store.py
│  └─ tests/
│
├─ engine/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  │  ├─ health.py
│  │  │  └─ tasks.py
│  │  ├─ models/
│  │  │  ├─ task_spec.py
│  │  │  └─ run_result.py
│  │  └─ services/
│  │     ├─ task_runner.py
│  │     └─ nanoclaw_adapter.py
│  └─ tests/
│
├─ bootstrap/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  │  └─ onboard.py
│  │  ├─ services/
│  │  │  ├─ ssh_bootstrap.py
│  │  │  ├─ package_installer.py
│  │  │  └─ subagent_deployer.py
│  │  └─ models/
│  │     └─ onboarding.py
│  └─ tests/
│
├─ skills/
│  ├─ sys.probe/
│  │  ├─ skill.yaml
│  │  └─ README.md
│  ├─ net.probe/
│  ├─ svc.probe/
│  ├─ fs.probe/
│  ├─ tool.lifecycle/
│  ├─ ops.onboard.two_node/
│  ├─ ops.health.bundle/
│  └─ report.evidence_pack/
│
├─ playbooks/
│  ├─ templates/
│  │  ├─ investigate_service_issue.yaml
│  │  ├─ onboard_two_nodes.yaml
│  │  └─ install_and_validate_tool.yaml
│  └─ generated/
│
├─ org_profiles/
│  ├─ defaults/
│  │  └─ baseline.yaml
│  └─ examples/
│     └─ campus_lab.yaml
│
├─ artifacts/
├─ audit/
├─ evidence/
└─ archive/
   └─ old_web_backup/
```

문서의 핵심 취지대로 **core / engine / subagent / bootstrap / web(ui)** 경계를 먼저 고정해야 땜질을 줄일 수 있다. 
또 Core는 직접 원격 작업을 하지 않고, 반드시 **A2A 또는 SSH adapter**를 통해서만 실행해야 한다. 

---

# 2. 각 프로그램의 책임

## 2.1 core

권위 있는 컨트롤 플레인이다.

담당:

* 프로젝트 상태
* audit / evidence / artifact
* LangGraph workflow
* Master 질의
* Tool/Skill/Playbook 선택
* 사용자 질문/승인
* SubAgent/A2A orchestration
* 필요 시 Engine 호출

금지:

* 직접 원격 쉘 실행

이건 문서의 `opsclaw-core` 정의와 동일하다. 

## 2.2 subagent

대상 시스템 위에서 Tool을 실제로 실행하는 데이터 플레인이다.

담당:

* shell script 실행
* 즉석 쉘 스크립트 실행
* file push/pull
* capability probe
* stdout/stderr/evidence 저장

Manager↔SubAgent 계약은 최소 `health`, `run_script`, `push_file/pull_file`, `capabilities`로 고정하는 것이 맞다. 

## 2.3 engine

선택적 실행 엔진 계층이다.

담당:

* TaskSpec 받아 격리된 실행
* NanoClaw adapter
* sandbox / local model / wrapper runtime

금지:

* 프로젝트 상태 권위
* 정책/승인
* audit/evidence 권위 저장

NanoClaw를 넣더라도 Core가 필요할 때만 Engine을 호출하고, 정책/증빙/워크플로 권위는 Core에 남겨야 한다. 

## 2.4 bootstrap

원격 초기 온보딩 전용이다.

담당:

* SSH 접속
* 필수 패키지 설치
* subagent 배포
* health 확인

## 2.5 skills / playbooks / org_profiles

* `skills/`: 검증된 실행 패키지
* `playbooks/`: 동적 생성 또는 템플릿 DAG
* `org_profiles/`: 조직별 운영 기준 저장

Skill은 입력/정책/검증/증빙을 포함해야 하고, YAML은 계약/메타데이터 위주로 쓰는 것이 맞다.  

---

# 3. 핵심 모듈명과 역할

## 3.1 core/app/models

### `playbook_ir.py`

다음 필드를 가진다.

* `goal`
* `context`
* `constraints`
* `unknowns`
* `probes`
* `decisions`
* `plan`
* `validate`
* `errors`
* `fixes`
* `replans`
* `iterations`

IR v0는 이 정도를 저장해야 재현성이 생긴다. 

### `action_ir.py`

LLM 출력의 최소 허용 형식이다.

* `actions`
* `resolved_inputs`
* `question`
* `approval_request`

이건 Probe Loop 설계문서의 Action IR v0와 맞춘다. 

### `tool_result.py`

* `exit_code`
* `stdout`
* `stderr`
* `evidence_refs`
* `changed_files`
* `started_at`
* `ended_at`
* `resource_hints`

ToolResult 표준은 이 계약으로 가는 게 맞다. 

### `resolution.py`

* `mode: AUTO|CONFIRM|ASK|APPROVAL`
* `resolved_inputs`
* `needs_clarification`
* `pending_approvals`
* `rationale`
* `evidence_map`

Critical input은 AUTO 금지라는 규칙을 여기서 강제해야 한다. 

## 3.2 core/app/services

### `llm_registry.py`

역할별 모델 선택.
문서에 나온 `resolve_llm_conn_for_role("master", target_id)` 방식과 맞춘다. 

### `planner_service.py`

자연어 목표 → 초기 PlaybookIR 초안 생성

### `probe_loop_service.py`

핵심 루프.

* unknown 추출
* probe 생성
* SubAgent 실행
* evidence 저장
* LLM 재판단
* 질문 축소
* 상한 반복

LLM Probe Loop는 비전 구현의 핵심 우선순위다. 

### `execution_service.py`

* action을 target별로 분배
* `subagent_http | ssh_direct | engine_sandbox | local_only` 실행 프로필 처리

### `validation_service.py`

목표 기반 검증.
“일부 커맨드 성공”은 기본 성공 기준으로 금지해야 한다. 

### `subagent_client.py`

* `/health`
* `/a2a/run_script`
* `/a2a/push_file`
* `/a2a/pull_file`
* `/capabilities`

### `engine_client.py`

* TaskSpec 송신
* RunResult 수신

### `org_profile_service.py`

조직 기준값 로드/병합

* 내부망 대역
* 로그 보관기간
* 인터페이스 정책
* 승인 정책

## 3.3 core/app/workflows/nodes

실제 LangGraph 노드다.

* `plan_node.py`
* `probe_node.py`
* `resolve_node.py`
* `execute_node.py`
* `validate_node.py`
* `replan_node.py`
* `report_node.py`

표준 사이클을 구조로 고정해야 한다. 

---

# 4. API 명세

## 4.1 Core API

### `GET /health`

기본 상태 확인

응답:

```json
{
  "ok": true,
  "service": "chassisclaw-core"
}
```

### `POST /projects`

프로젝트 생성

요청:

```json
{
  "name": "suricata-inline-install",
  "request_text": "원격 서버 2대에 subagent 설치하고 상태 확인해줘",
  "target_ids": ["remote-1", "remote-2"]
}
```

응답:

```json
{
  "project_id": "prj_001",
  "status": "created"
}
```

### `GET /projects/{project_id}`

프로젝트 상태 조회

응답 핵심:

```json
{
  "project_id": "prj_001",
  "status": "running",
  "stage": "probe",
  "plan_ir": {},
  "run_ir": {},
  "last_questions": [],
  "pending_approvals": []
}
```

### `POST /projects/{project_id}/run_auto`

핵심 자동 실행 엔드포인트

동작:

* plan
* probe loop
* resolve
* execute
* validate
* replan
* report

문서에서도 `run_auto`를 LLM probe loop 기반으로 재구성하는 것이 직접 TODO로 적혀 있다. 

요청:

```json
{
  "max_iterations": 3,
  "policy_profile": "default",
  "allow_engine": false
}
```

응답 예시 1: 진행 완료

```json
{
  "status": "completed",
  "stage": "report",
  "summary": "2개 노드 온보딩 완료",
  "artifact_refs": ["art_001", "art_002"]
}
```

응답 예시 2: 질문 필요

```json
{
  "status": "needs_clarification",
  "stage": "resolve",
  "question": {
    "type": "policy",
    "field": "internal_cidr",
    "text": "내부망으로 취급할 CIDR 범위를 선택해줘",
    "choices": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
  }
}
```

응답 예시 3: 승인 필요

```json
{
  "status": "needs_approval",
  "stage": "resolve",
  "approval_request": {
    "field": "fw_apply",
    "text": "방화벽 룰 적용은 고위험 작업이다. 승인할까?"
  }
}
```

### `POST /projects/{project_id}/answer`

질문 응답 저장

문서상 최소 질의 endpoint는 반드시 필요하다. 

요청:

```json
{
  "answers": {
    "internal_cidr": "10.10.0.0/16",
    "log_retention_days": 180
  }
}
```

### `POST /projects/{project_id}/approve`

고위험 작업 승인

요청:

```json
{
  "approvals": {
    "fw_apply": true,
    "service_restart": false
  }
}
```

### `POST /targets`

타겟 등록

요청:

```json
{
  "target_id": "remote-1",
  "host": "10.10.0.21",
  "port": 55123,
  "mode": "subagent_http",
  "tags": ["linux", "edge"]
}
```

### `GET /targets`

등록 타겟 조회

### `GET /targets/{target_id}/health`

타겟 health 조회

### `POST /llm/connections`

LLM connection 등록

### `POST /llm/roles`

역할별 모델 바인딩

문서에서 role-based master 연결이 이미 중요하게 다뤄진다. 

### `GET /artifacts/{artifact_id}`

보고서/zip 다운로드

---

## 4.2 SubAgent API

문서상 허용 계약 그대로 간다. 

### `GET /health`

### `GET /capabilities`

응답 예시:

```json
{
  "ok": true,
  "sudo": true,
  "systemctl": true,
  "docker": false,
  "package_manager": "apt",
  "python": "3.12",
  "node": null
}
```

### `POST /a2a/run_script`

요청:

```json
{
  "run_id": "run_001",
  "target_id": "remote-1",
  "script": "ip -o link show\nip route\n",
  "timeout_s": 30
}
```

응답:

```json
{
  "ok": true,
  "exit_code": 0,
  "stdout": "...",
  "stderr": "",
  "evidence_refs": ["ev_001"],
  "changed_files": []
}
```

### `POST /a2a/push_file`

### `GET /a2a/pull_file`

---

## 4.3 Engine API

NanoClaw 통합 전에도 계약은 먼저 만든다. 

### `GET /health`

### `POST /tasks/run`

요청:

```json
{
  "task_id": "task_001",
  "task_type": "tool_lifecycle",
  "working_dir": "/workspace",
  "mounts": [],
  "env_refs": [],
  "timeout_s": 120,
  "payload": {
    "goal": "install and run tool X"
  }
}
```

응답:

```json
{
  "ok": true,
  "exit_code": 0,
  "stdout": "...",
  "stderr": "",
  "artifacts": ["/workspace/report.json"],
  "evidence_refs": ["eng_001"]
}
```

---

# 5. IR 스키마 최소안

## 5.1 PlaybookIR

```json
{
  "goal": "원격 2노드 온보딩",
  "context": {},
  "constraints": {},
  "unknowns": ["sudo_available", "pkg_manager"],
  "probes": [],
  "decisions": [],
  "plan": {
    "jobs": [],
    "steps": []
  },
  "validate": [],
  "errors": [],
  "fixes": [],
  "replans": [],
  "iterations": 0
}
```

## 5.2 ActionIR

문서상 최소 허용 출력과 맞춘다. 

```json
{
  "actions": [
    {
      "id": "p1",
      "type": "shell",
      "target_id": "remote-1",
      "timeout_s": 30,
      "script": "ip -o link show\nip route\n"
    }
  ],
  "resolved_inputs": {
    "iface_in": "ens33"
  },
  "question": null
}
```

---

# 6. Skill 디렉터리 표준

문서 권장 구조를 그대로 채택한다. 

예:

```text
skills/net.probe/
├─ skill.yaml
├─ README.md
├─ runner.sh           # optional
└─ wrapper/            # optional
```

`skill.yaml` 기본 필드:

* `id`
* `version`
* `risk`
* `approval_required`
* `inputs`
* `outputs`
* `policy_profile`
* `execution_profile`
* `steps`
* `validate`
* `evidence`

Skill 계약에는 입력/정책/증빙이 반드시 포함돼야 한다. 

---

# 7. 첫 마일스톤 구현 순서

첫 마일스톤은 **M1. Tool-Centric Core + LLM Probe Loop v0** 로 가는 게 맞다.
이유는 문서상 비전 구현의 핵심 P0가 바로 **LLM Probe Loop 엔진**, **Human 최소 질의 endpoint**, **IR 도입**이기 때문이다. 

## 단계 1. 레포 경계 정리

목표:

* core / subagent / engine / bootstrap / skills 디렉터리 확정
* 기존 backup web 분리
* 공통 storage 경로 확정

작업:

1. 디렉터리 구조 생성
2. `archive/old_web_backup` 이동
3. `.env.example`, `docker-compose.yml`, `README.md` 기본 작성
4. core/subagent health만 우선 살아있게 정리

완료조건:

* `docker compose up` 후 core/subagent health OK

## 단계 2. Core 모델 뼈대

작업:

1. `project.py`, `target.py`, `playbook_ir.py`, `action_ir.py`, `resolution.py`, `tool_result.py`
2. `json_store.py`, `project_store.py`, `audit_store.py`, `evidence_store.py`
3. `AuditEvent` 타입 정의
4. 오류 응답 JSON 표준화

문서에서도 오류 응답 JSON 표준화는 안정화 우선순위다. 

완료조건:

* 프로젝트 생성/조회
* 타겟 등록/조회
* audit/evidence 디렉터리 생성

## 단계 3. SubAgent 표준화

작업:

1. `/health`
2. `/a2a/run_script`
3. `/capabilities`
4. `/a2a/push_file`, `/a2a/pull_file`
5. ToolResult 형식 통일
6. stdout/stderr 무조건 evidence 저장

이 부분은 문서의 A2A 계약과 ToolResult 표준 그대로다.  

완료조건:

* Core에서 SubAgent로 shell probe 1개 실행 가능

## 단계 4. LLM Registry + 역할 바인딩

작업:

1. `POST /llm/connections`
2. `POST /llm/roles`
3. `llm_registry.resolve_llm_conn_for_role("master", target_id)`

완료조건:

* master role에 연결된 모델로 test call 가능

## 단계 5. `run_auto` 뼈대

작업:

1. `POST /projects/{id}/run_auto`
2. 내부에서 `planner_service` 호출
3. `PlaybookIR` 초기화
4. target/answers/org_profile 병합

완료조건:

* `run_auto` 호출 시 plan_ir 생성됨

## 단계 6. Probe Loop v0

작업:

1. `probe_loop_service.py` 생성
2. 프롬프트 계약 정의
3. LLM 출력은 `actions|resolved_inputs|question`만 허용
4. `shell` action은 SubAgent `/a2a/run_script`로 실행
5. 결과를 evidence/audit에 저장
6. max_iter=3, timeout 적용

이건 기존 구현 문서의 목표와 정확히 같다. 

완료조건:

* iface 탐색 같은 missing input 자동 해결
* 또는 질문 1개로 축소

## 단계 7. 질문/승인 루프

작업:

1. `POST /projects/{id}/answer`
2. `POST /projects/{id}/approve`
3. state에 answers/approvals 저장
4. run_auto 재호출 시 반영

완료조건:

* policy 질문을 받은 뒤 재실행 가능

## 단계 8. Validate/Replan 최소 구현

작업:

1. `validation_service.py`
2. 목표 기반 validate rule 1개 이상 필수
3. fail 시 replan 진입
4. 일부 실패 시 probe→fix→retry 1회

문서의 기본 규칙대로 “일부 커맨드 성공”은 통과 기준으로 삼지 않는다. 

완료조건:

* 실패 후 1회 재계획 동작

## 단계 9. 첫 대표 Skill: `ops.onboard.two_node`

문서에서 첫 대표 Skill을 2노드 온보딩으로 고정하는 것이 적절하다고 되어 있다. 

작업:

1. 두 노드 SSH/subagent 상태 확인
2. capabilities probe
3. 필요한 패키지 설치
4. subagent 배포
5. health 검증
6. evidence pack 생성

완료조건:

* 2개 노드에서 온보딩 성공
* 실패 시 질문 또는 재시도

---

# 8. 첫 마일스톤의 테스트 시나리오

문서에 나온 테스트 케이스를 그대로 채택하면 된다. 

## 시나리오 A. missing input 자동 해결

요청:

* “suricata inline install 해줘”

기대:

* iface_in/out 미지정
* LLM이 `ip -o link show`, `ip route` probe 생성
* 자동 확정 또는 질문 1개로 축소

## 시나리오 B. 모호한 플레이북 선택

요청:

* “점검해줘”

기대:

* probe로 상태/대상 특성을 확인
* playbook 후보를 줄이거나 질문 1개 생성

## 시나리오 C. 실패 후 재계획

요청:

* 설치 중 일부 step 실패 유도

기대:

* stderr/evidence 기반으로 원인 파악 probe 생성
* 수정 action 실행 후 재시도

---

# 9. 첫 커밋 단위 추천

## Commit 1

`repo: split chassisclaw into core subagent engine bootstrap skills`

## Commit 2

`core: add base models stores and health endpoints`

## Commit 3

`subagent: add run_script capabilities and evidence store`

## Commit 4

`core: add llm registry and role bindings`

## Commit 5

`core: add run_auto skeleton and playbook ir`

## Commit 6

`core: implement probe loop v0 with action ir`

## Commit 7

`core: add answer approve endpoints and state merge`

## Commit 8

`core: add validate replan loop v0`

## Commit 9

`skills: add ops.onboard.two_node initial skill`

---

# 10. 최종 고정안

한 줄로 고정하면 이렇다.

**ChassisClaw는 core가 LangGraph 상태기계와 audit/evidence 권위를 갖고, master가 probe/action/question을 생성하며, manager가 이를 orchestration하고, subagent가 Tool(OS 명령어, 동적 쉘 스크립트, OSS 설치·실행)를 수행하고, 그 stdout/stderr/evidence를 다시 루프에 넣어 재계획하는 구조로 구현한다. NanoClaw는 필요 시 engine 계층으로만 통합한다.**   

다음으로 바로 이어서 원하면, 이 구조 기준으로 **M1에 해당하는 실제 파일별 초안 코드 골격**까지 바로 써주겠다.
