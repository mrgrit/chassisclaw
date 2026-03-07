좋아. 아래는 **지금까지 너랑 겪은 실제 문제들(땜질 루프 / iface 지옥 / sudo 없음 / 컨테이너 네트워크 착시 / 원격 온보딩 / repo 꼬임 / internal server error / 모듈 경계 붕괴)**을 **설계 스펙에 “강제 구조”로 반영**해서, 네가 올려둔 “NanoClaw 엔진 랩핑 + OpsClaw 고유 설계 얹기” 문서를 **업데이트한 “전체 시스템 구성 스펙(매우 상세)”**이다.
(분량 줄이지 말라고 했으니 그대로 길게, 대신 **앞뒤 논리/경계/절차/실행 위치**를 명확히 박아둘게.)

---

# 0) 변경 이유(필수 전제) — “왜 여기까지 왔는지”를 설계에 박는다

## 0.1 우리가 실제로 겪은 “땜질 루프”의 근본 원인

1. **경계가 없다**: “어디서 실행해야 하는지(Manager? SubAgent? 원격?)”가 매번 흐려져서, 실행 위치가 섞이며 오류가 재발했다.
2. **사소한 변수의 폭발**: iface / sudo / systemctl / docker / sshd 같은 “환경 차이”가 매번 새로 등장했고, 그때마다 로직이 덧붙으면서 누더기가 됐다.
3. **추측 기반 자동결정**: net.probe가 컨테이너 환경에서 eth0 같은 착시를 만들어도 “자동 확정”이 들어가면서 사용자 기대와 충돌했다.
4. **실행-검증-증빙 계약이 약함**: 실행 단계가 성공처럼 보이는데(“at_least_one_command_succeeded” 같은 룰) 실제 목표는 실패(예: 설치 안됨)해도 “패스” 처리되는 설계가 섞였다.
5. **온보딩(원격 설치) 경로가 미정**: subagent가 없는 원격을 어떻게 다룰지(ssh direct vs bootstrap) 경로가 고정되지 않아, “2노드 온보딩”에서 계속 맴돌았다.

## 0.2 이번 스펙의 핵심 목표

* **사소한 변수가 나오더라도 구조가 무너지지 않게**
* “땜질”이 아니라 **규칙/계약/분리**로 해결되게
* 컨텍스트가 쌓여도 잊어버려도 되게: **4~5개 독립 프로그램(패키지)로 분리**
* NanoClaw를 쓰더라도 통제는 OpsClaw가 하게: **엔진은 바깥, 권위/정책은 Core**

---

# 1) 최종 제품 정의(정체성 그대로, 하지만 ‘강제 구조’ 포함)

## 1.1 한 줄

**자율시스템 지향, 자연어로 서버·클라우드·네트워크·보안·엔드포인트 작업을 수행하는 멀티 AI 에이전트 오케스트레이터.**

## 1.2 두 줄

사용자가 목표를 제시하면, 시스템은 **필요한 것만 질문**하고 계획을 수립한 뒤 작업을 분해해 타겟(SubAgent/SSH)에 배분하고 협업을 조율한다. 세부 계획과 Todo를 생성해 작업 체계를 구축한다.
에이전트는 상황에 맞는 동적 프롬프트/스크립트/툴/OSS를 사용해 실행하고, 결과를 Evidence로 남기며 검증 후 다음 스텝을 반복해 목표를 끝까지 완수한다.

## 1.3 세 줄(중요: “폭주 방지”를 선언이 아니라 구조로)

경량 오픈 모델 중심으로 폐쇄망 운용이 가능하고, 어려운 문제는 Master(상용모델)에 **최소한의 질문만** 보내 해결한다.
LLM이 자율로 수행하되 **Playbook/Skill 기반 실행 계약 + 승인 게이트 + 증빙 검증**으로 폭주를 방지하고, 마일스톤별 테스트/리포트/검수로 품질을 보장한다.
**Tool/Skill/Experience** 모듈화로 작업을 구조화하고, 누적 지식과 (장기적으로) RL/밴딧 최적화로 질문을 줄이며 자율화를 강화한다.

---

# 2) 전체 시스템 구성(“4~5개 독립 프로그램” 기준)

> 네가 원하는 “컨텍스트가 쌓이면 앞을 잊고 국소 문제에 집착 → 땜질”을 막기 위해
> **프로그램을 독립적으로 쪼개서**, 하나 끝나면 이전을 잊어도 다음을 진행할 수 있게 한다.

## Program A — `opsclaw-core` (Control Plane, 권위/정책/상태)

* 역할: **프로덕트의 중심**

  * 프로젝트/상태(State)/감사(Audit)/증빙(Evidence)/아티팩트(Report/Zip) 저장의 **Single Source of Truth**
  * LangGraph 워크플로(상태기계) 실행
  * Skill/Experience 레지스트리
  * MasterGate + Master Review
* 금지: “여기서 직접 원격 OS 작업” 금지. 반드시 A2A/SSH Adapter 통해서만.

## Program B — `opsclaw-engine` (NanoClaw 랩핑 런타임)

* 역할: **실행 엔진**

  * NanoClaw를 그대로 포함(vendor/submodule)하되, 외부에 “NanoClaw”를 노출하지 않음
  * Core가 정의한 **TaskSpec 계약**을 받아 실행하고 **RunResult**로 반환
  * (선택) 로컬 모델/세션/컨테이너 샌드박스 실행 제공
* 핵심: NanoClaw는 “기능”은 해주지만, **정책/증빙의 권위는 없다**.

## Program C — `opsclaw-subagent` (Data Plane, 타겟 실행기)

* 역할: 타겟에서 스크립트 실행 / 파일 입출력 / 증빙 수집
* 설치 방식: docker 버전 + 향후 standalone(1-shot bootstrap)
* 원칙: **SubAgent는 “실행기”**일 뿐, 플래닝/정책 판단은 하지 않는다.

## Program D — `opsclaw-remote-bootstrap` (원격 온보딩 전용)

* 역할: “subagent 없는 원격”을 **한방에** subagent 가능한 상태로 만든다

  * sshd 설치/기동
  * 계정 생성/키 배포
  * 필수 패키지(curl/jq/git/ca-cert) 설치
  * subagent 배포(파일 전송 or git clone) 및 서비스 실행
* 이유: 온보딩은 매번 터진다 → Core/워크플로랑 섞지 말고 “전용 프로그램/전용 Skill”로 고정.

## Program E — `opsclaw-ui` (Web UI)

* 역할: 프로젝트 생성/진행/승인/증빙 다운로드/노드별 상태 확인

> 이 구조의 효과:
> A(코어) 개발이 막히면 B/C/D는 그대로 유지,
> D(온보딩)만 고치면 원격환경은 매번 재현 가능,
> B(NanoClaw) 업데이트는 엔진 내부에서만 해결.

---

# 3) “NanoClaw를 Core로 랩핑” 전략 — 역할/장단점/통제 가능성

## 3.1 결론(명확히)

* **좋은 생각이 될 수 있다. 단, “Core에 포함”이 아니라 “Engine으로 분리”할 때만.**
* Core에 NanoClaw 코드를 섞는 순간, 지금 너가 싫어하는 “경계 붕괴 → 땜질”이 더 커진다.

## 3.2 NanoClaw의 역할(OpsClaw 안에서 무엇을 담당?)

NanoClaw는 OpsClaw에서 **딱 이 역할만** 맡긴다:

1. **실행 런타임**: 세션/프로세스/컨테이너 샌드박스/워크스페이스 마운트/툴 실행
2. **로컬 모델 호출 파이프라인**(폐쇄망 운영에서 특히 유용)
3. **엔진 안정성**(재시도/타임아웃/스트리밍/자원 관리)

NanoClaw에게 **절대 맡기면 안 되는 것**(OpsClaw Core 고유):

* 프로젝트 상태/감사/증빙의 권위
* 승인/정책/기밀 필터링(MasterGate)
* Skill/Experience 레지스트리
* LangGraph 워크플로(Plan→Probe→Resolve→Execute→Validate→Report)

## 3.3 OpsClaw 안에서 NanoClaw가 “작동한다”는 의미

* “OpsClaw 전체가 NanoClaw 위에서 돈다”가 아니라,
* **OpsClaw Core가 필요한 때에만 Engine(NanoClaw 랩퍼)을 호출**하는 구조다.

즉 호출 흐름은 이렇게 고정:

* UI/API → Core(Manager) → (필요 시) Engine(NanoClaw) → (필요 시) SubAgent/A2A → 결과 회수 → Core가 상태/증빙 저장

## 3.4 OpsClaw 개발이 쉬워지나? 복잡해지나?

* **초기엔 복잡해질 수 있다**: 경계/계약(TaskSpec/RunResult) 정의가 필요해서.
* **중장기엔 압도적으로 쉬워진다**:
  엔진(실행) 문제를 코어(정책/워크플로)에서 분리해버리니까 “땜질이 줄어든다.”

## 3.5 “오픈소스인데 통제가 완벽히 가능하냐?”에 대한 현실적 답

* **완벽 통제는 불가능**(남의 코드니까).
* 하지만 “통제가 필요한 영역”을 좁히면 가능해진다:

  * NanoClaw를 직접 믿는 게 아니라,
  * Core↔Engine 사이에 **계약 + 샌드박스 + 관측 + 제한**을 둬서 통제한다.

통제 장치(필수):

* Engine 호출은 전부 **TaskSpec**으로만(임의 실행 금지)
* Tool 실행은 allowlist/denylist + working dir 제한 + output bytes 제한
* 실행 결과는 반드시 evidence로 수집 (stdout/stderr/file refs)
* Engine 업데이트는 “엔진만” 교체 가능

---

# 4) 핵심 뼈대: LangGraph + A2A (이번엔 “추상” 말고 “계약”으로)

## 4.1 LangGraph: 표준 상태기계(노드 계약 포함)

### Graph: `Plan → Probe → Resolve → Execute → Validate → Replan(loop) → Report`

각 노드는 반드시 아래 계약을 갖는다.

#### (1) Plan 노드

* Input: `request_text`, `targets`, `skills_registry`, `policy_profile`
* Output: `PlanIR`

  * selected_skill(or workflow)
  * target set(1..N)
  * initial assumptions
  * required facts list(unknowns)
  * risk classification
  * milestone checklist (테스트/리포트 요구 포함)

#### (2) Probe 노드 (Evidence-first)

* Input: `PlanIR`, `Target`
* Output: `ProbeBundle`

  * sys/svc/net/fs 결과 (facts + unknowns + rationale + evidence_refs)
* 규칙:

  * **probe 결과 없이는 Resolve가 결론 내리면 안 됨**
  * “컨테이너 환경” 같은 경우를 **명시적으로 표기**해야 함(너희가 이미 구현 시작함)

#### (3) Resolve 노드 (AUTO/CONFIRM/ASK/APPROVAL)

* Input: `ProbeBundle`, `Skill inputs spec`, `Experience hints`
* Output: `Resolution`

  * resolved_inputs
  * needs_clarification 질문
  * pending approvals
  * rationale + evidence_map
* 핵심 강제 규칙(땜질 방지):

  * **Critical decision class**는 AUTO 금지(무조건 CONFIRM)
  * 환경이 “불확실(confidence low)”이면 AUTO 금지(무조건 CONFIRM)

#### (4) Execute 노드

* Input: `Skill`, `resolved_inputs`, `Target`, `execution_profile`
* Output: `ExecResult`

  * step runs (exit_code, stdout/stderr refs, changed_files)
* 강제:

  * 실행은 반드시 A2A(또는 SSH Adapter)로만
  * stdout/stderr는 무조건 evidence로 저장

#### (5) Validate 노드 (구라 방지)

* Input: `ExecResult`, `validate rules`, `ProbeBundle (re-run)`
* Output: `ValidationResult`

  * pass/fail + why + evidence refs
* 강제:

  * “일부 커맨드 성공” 같은 룰은 **V1 기본값 금지**
  * 목표 기반(예: service active, port listen, file exists, version check) 검증을 기본으로

#### (6) Replan 노드

* Input: 실패 원인 / evidence / 후보 전략
* Output: 다음 PlanIR 업데이트 or “human required”

#### (7) Report 노드

* Input: 전체 audit/evidence
* Output: Report + EvidencePack(zip)

## 4.2 A2A: 분산 실행 계약(필수 고정)

Manager ↔ SubAgent는 아래만 허용:

* `health`
* `run_script`
* `push_file / pull_file`
* (선택) `capabilities` (sudo/systemctl/docker/apt 등 환경 특성)

---

# 5) Tool / Skill / Experience — “땜질 안 되게” 정형화

## 5.1 Tool (실행 단위) — 계약 고정

Tool = “지금 실행 가능한 것”

* shell script
* OSS 설치/실행
* CLI/API 호출

**ToolResult 표준**

* exit_code
* stdout/stderr
* evidence_refs
* changed_files
* started_at/ended_at
* resource hints(optional)

## 5.2 Skill (검증된 실행 패키지) — “입력/검증/증빙”이 반드시 포함

Skill YAML(IR) 필수 섹션:

* inputs: 타입/필수/질문/후보생성(discover)/중요도(critical 여부)
* policy_profile: 위험도/승인 필요 조건
* execution_profile: `subagent_http | ssh_direct | local_only | engine_sandbox`
* steps: 명령/툴/파일 작업
* validate: **목표 기반** 규칙(최소 1개)
* evidence: 수집 규칙

**중요: “Critical input” 플래그**

* iface 같은 것만이 아니라

  * firewall rule
  * account lock
  * delete/move
  * production restart
  * route change
  * key install
  * 비용 발생(cloud)
* 이런 건 모두 `critical: true` 로 표기하고 Resolve에서 AUTO 금지

## 5.3 Experience (기억) — “사람 선택을 저장하되, 검증 조건과 함께”

Experience를 3타입으로 분리(이게 없으면 오판 저장으로 땜질 난다):

1. **Preference**: 사용자/조직 선호(예: 계정명, 표준 경로)
2. **Fact-hint**: 특정 환경에서 반복되는 사실(예: 이 환경은 sudo 없음)
3. **Strategy**: 성공한 해결 전략(예: “systemd 없음 → service 사용”)

저장 규칙:

* 저장 시 반드시:

  * 적용 조건(when): OS/target tags/hostname pattern 등
  * 검증(probe rule): 적용 전에 확인할 probe 규칙
* “한 번 성공”은 장기기억이 아니라 short-term → 누적되면 승격(RL/밴딧 예정)

---

# 6) “원격 온보딩(2노드 이상)” — 이번 스펙에서 핵심 Skill로 고정

너는 이미 실제로 했다. 이제는 “다시 할 수 있게” 고정해야 한다.

## 6.1 Target 모델(2가지 경로를 명시)

Target = { id, host, port, user, auth, mode }

* mode:

  1. `subagent_http` : 이미 55123 health 되는 노드
  2. `ssh_direct` : subagent 없는 노드(bootstrap 필요)
* auth:

  * ssh key ref(Manager에 있는 키)
  * password는 원칙적으로 “최초 1회”만(그 이후 key로 전환)

## 6.2 Bootstrap Skill: “한방 스크립트”로 만들 영역(Program D)

Bootstrap은 Core/Engine과 분리된 전용 구성으로 간다.

* sshd 설치/기동
* 사용자 생성(work1/work2 같은)
* authorized_keys 세팅(권한 700/600/chown)
* 필수 패키지 설치(curl/jq/git/ca-cert)
* repo clone
* subagent 실행(도커 있으면 도커, 없으면 standalone)

**핵심: sudo 가정 금지**

* 너희가 겪은 것처럼 sudo 없을 수 있다.
* bootstrap은 다음 순서로 판단:

  1. 현재 user가 root면 sudo 없이 진행
  2. root가 아니고 sudo 있으면 sudo 사용
  3. 둘 다 아니면 “승인/수동 필요”로 종료

## 6.3 Onboarding DAG(멀티 노드 병렬)

1. Reachability/SSH 확인
2. capability probe (root? sudo? apt? systemctl? docker?)
3. bootstrap 실행(필요 시)
4. subagent health 확인
5. 표준 probe(sys/svc/net/fs)
6. evidence pack + node matrix report

---

# 7) Evidence / Audit / Report — “실제 제출 가능한 형태”로

## 7.1 Audit 이벤트 표준(너희가 이미 쌓아온 타입들을 정리)

* PROJECT_CREATED
* TARGET_REGISTERED / TARGET_UPDATED
* WORKFLOW_STARTED / WORKFLOW_DONE
* PROBE_SYS/SVC/NET/FS
* RESOLVE_AUTO / RESOLVE_CONFIRM / RESOLVE_ASK / RESOLVE_APPROVAL
* EXEC_STEP_START / EXEC_STEP_DONE
* VALIDATE_PASS / VALIDATE_FAIL
* REPLAN
* REPORT_GENERATED / EVIDENCE_PACK_CREATED

## 7.2 Evidence Pack(Zip) 최소 구성

* audit.jsonl
* run results (step별 stdout/stderr)
* diff(가능 시)
* tool install logs
* version/capability snapshot
* report.md (+pdf 선택)

---

# 8) API 스펙(“어디서 실행하냐” 문제를 없애기 위해 명확화)

## 8.1 Core Manager API(외부)

* `POST /projects`
* `GET /projects/{id}`
* `POST /projects/{id}/run`  ← LangGraph workflow 실행
* `POST /projects/{id}/approve`
* `GET /artifacts/{id}`
* `GET /health`

## 8.2 Probe API

* `POST /probe/sys|svc|net|fs`
  (Probe는 “대상에서 실행”되는 거고, 호출 주체는 Core)

## 8.3 A2A API(Core ↔ SubAgent)

* `POST /a2a/run_script`
* `POST /a2a/push_file`
* `GET /a2a/pull_file`
* `GET /health`

## 8.4 Engine API(Core ↔ NanoClaw Wrapper)

* `POST /engine/task/run`

  * input: TaskSpec (tool run / session message / sandbox run)
  * output: RunResult (evidence refs 포함)

**중요**: “사용자가 어디서 실행할지 헷갈리는” 문제는 API 레벨에서 막는다.

* 사용자가 remote에서 뭔가 하라고 복붙하는 방식은 “문서/가이드”로만
* 실제 실행은 Core API 호출로만(웹UI나 curl로 Core를 때리면 된다)

---

# 9) 레포를 갈아엎을지 vs 현재 위에 올릴지(현실적인 기준)

## 9.1 From scratch가 “맞는 경우”

* 지금 레포가 “경계 붕괴(legacy/manager_api/api 혼재)”로
  어느 코드가 권위인지 계속 헷갈리고, 수정할수록 사이드이펙트가 커지는 상태라면
* 특히 “core import 경로 꼬임 / 내부 모듈 경로 불명 / 실행 경로 혼선”이 반복되면
  → **from scratch가 더 싸다**.

## 9.2 현재 상태에서 NanoClaw 올리는 게 “가능한 경우”

가능은 하다. 조건은 1개:

* NanoClaw를 **engine/**로 넣고, Core는 `engine_client`로만 호출
* 절대 “Core 코드 안에 NanoClaw 로직을 섞지 않는다”

이 조건을 지키면, 지금 레포 위에도 충분히 올릴 수 있다.

---

# 10) 22개 User Case “전부” 수행 가능한 설계로 확장하는 방법(도메인 커버리지)

22개 케이스를 전부 “하나의 만능 스킬”로 만들지 않는다.
**도메인별 최소 스킬 번들**로 만든다(이게 땜질 방지).

* Incident/Health: `ops.health.bundle`
* Onboarding: `ops.onboard.multi_node`
* Compliance: `sec.baseline.audit` / `sec.remediate`
* Network Diagnosis: `net.diagnose.path`
* OSS Adoption: `tool.discover.install.wrap`
* Reporting: `report.weekly`, `report.evidence_pack`

각 번들의 공통 바닥은:

* probe(sys/svc/net/fs)
* resolve(AUTO/CONFIRM/ASK/APPROVAL)
* execute
* validate
* report

---

# 11) “다음 작업” (이제부터 뭘 먼저 만들지)

너가 원한 “한 번에 끝내는 방식 + 땜질 최소화” 기준으로, 순서는 이렇게 고정이 맞다.

## Step 1) Repo 구조를 “프로그램 4~5개”로 분리 (최우선)

* core/
* engine/ (nanoclaw vendored)
* subagent/
* bootstrap/
* web/

이거 먼저 안 하면, 또 어디가 뭘 하는지 섞여서 땜질된다.

## Step 2) Core ↔ Engine 계약(TaskSpec/RunResult) 먼저 만든다

* “NanoClaw를 Core로 가져온다”의 실체는 이것이다.
* 이거 없으면 NanoClaw 통제 불가능.

## Step 3) 첫 대표 Skill은 “2노드 온보딩”으로 고정

* 이미 너가 해낸 절차를 “Skill로 고정”해서 다시는 헤매지 않게 한다.
* 이 Skill이 통과하면, 나머지 22개는 같은 템플릿으로 확장 가능.

---

# 12) 너 질문들에 대한 짧은 결론(하지만 이번엔 문서에 반영됨)

* NanoClaw를 Core로 랩핑?
  → **Core에 섞지 말고 Engine으로 분리하면 좋은 생각.**

* NanoClaw 역할?
  → **실행 런타임(세션/툴/샌드박스/로컬모델) 전담. 정책/증빙/워크플로는 Core.**

* OpsClaw 안에서 NanoClaw 작동?
  → **Core가 내부적으로 엔진 호출하는 형태. OpsClaw=NanoClaw가 아님.**

* 레포 갈아엎기?
  → 지금처럼 경계가 계속 붕괴하면 **from scratch가 더 싸다**.
  단, “분리 구조”만 지키면 현재 레포에서도 engine 얹기는 가능.

* 실현 불가능?
  → **가능.** 단, “경계/계약/분리” 없으면 개발 방식이 불가능해진다. 지금 그 상태였고, 이 스펙은 그걸 막기 위한 설계다.

---