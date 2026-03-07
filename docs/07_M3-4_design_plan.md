# M3 수정 계획 (M3-4 재정의: 멀티타겟 오케스트레이션 중심)

> 상태: **M3-1, M3-2, M3-3 기능은 “완성(동작)” 단계**에 도달.  
> 남은 핵심은 **M3-4**이며, 이는 단순 “플레이북/RAG 통합”이 아니라  
> **멀티 타겟 작업 분해 → 자동 배분 → 분산 실행 → 연관 작업 조율 → 진행상황/증빙**까지 포함해야 한다.

---

## 0) 왜 계획을 수정했나 (요구사항 정밀화)
사용자 시나리오가 “한 서버에 하나 작업” 수준이 아니라,

- 서버1: Suricata 설치/인라인 구성  
- 서버2: OPNsense 설치/기본 설정  
- 서버3: Nginx+ModSecurity+DVWA 설치/검증

처럼 **서로 다른 타겟에 서로 다른 스택을 동시에 배치**하고,  
결과가 서로 연관(예: WAF 경로, IPS 인라인 경로)되어 있어 **작업 간 조율**이 필요해졌다.

따라서 M3-4는 다음을 충족하도록 재정의한다:

1) **LLM은 “계획(WorkItems)”만 산출**한다 (배분/실행은 시스템이 책임)  
2) **배분은 Router(규칙 기반)**가 한다 (tags/capabilities 기반 best-fit)  
3) **소통은 subagent 간 직접 통신이 아니라 Manager가 중재하는 Event/State 버스**로 처리한다  
4) **진행상황은 Project Dashboard(상태/마일스톤/증빙)로 가시화**한다

---

## 1) 현재 M3-1/2/3 완료 정의 (정리)

### M3-1 Archive/Retention + 조회
- ✅ Approval Archive/Restore, include_archived/only_archived 조회
- ✅ Retention/Purge 엔드포인트 및 디렉토리 정리
- ✅ 운영 큐 폭발 방지 기능 확보

### M3-2 RBAC/감사
- ✅ 토큰 기반 역할(RBAC) 적용(viewer/operator/approver/admin)
- ✅ 주요 이벤트 audit(JSONL) 기록
- ✅ web에서 토큰 저장(쿠키) + 프록시 호출 기반 마련

### M3-3 Master reply JSON schema 강제 + parser 안정화
- ✅ 스키마 강제 + 파서(재시도/추출) 안정화
- ✅ sanitize(placeholder/denylist)로 위험 커맨드 제어
- ⚠️ 단, “설치/운영 작업”에는 denylist가 과도함 → **M3-4에서 execution_profile 분리로 해결**

---

## 2) 수정된 M3-4 목표 (핵심 UX로 환원)

> “사용자 작업 요청 → 시스템이 알아서 분해/배분/실행/검증/재시도 → 막히면 MasterGate 승인 후 Master 질의 → 마일스톤별 대시보드”

이를 위해 M3-4는 아래 5개 서브마일스톤으로 쪼갠다.

---

# 3) M3-4 서브마일스톤 (수정본)

## M3-4.1 Targets Registry (자산/실행지 정의)
### 목표
- “어느 서버에서 실행할지”를 명시/자동 선택할 수 있도록 **Target(=SubAgent endpoint) 등록**을 제공
- 이후 모든 실행은 `target_id -> subagent_url`로 라우팅

### 범위
- `/targets` CRUD
- Target metadata:
  - `id`, `base_url`
  - `tags`(suricata/opnsense/waf 등)
  - `capabilities`(apt/systemd/docker/nftables 등, 선택)
  - `role`(sensor/gateway/web/jump 등, 선택)
- Project에 default target(s) 연결 가능

### 완료 기준
- playbook 실행 시 target_id로 원격 subagent에 라우팅 성공
- 더 이상 `ssh ...` 커맨드 의존 없이 “원격에서 로컬 실행” 가능

---

## M3-4.2 Playbook Runner (타겟별 절차 실행기)
### 목표
- “설치/구성/검증”을 **Playbook 단계**로 실행
- 결과가 state/audit/evidence에 자동 누적

### 범위
- `api/playbooks/*.yaml` (2~3개 샘플)
- `run_playbook` 실행기:
  - steps 순차 실행
  - stop-on-fail(MVP)
  - validate rule 최소 지원
- `/playbooks`, `/playbooks/{id}`, `/projects/{id}/run_playbook`

### 완료 기준
- 최소 1개 플레이북이 원격 타겟에서 실행되고 pass/fail을 반환
- evidence/audit/state에 기록 누적

---

## M3-4.3 WorkItem Plan + Router (자동 배분/멀티타겟 오케스트레이션)
### 목표
- LLM이 “알아서 배분”하는 것처럼 보이되,
  - 실제로는 **LLM은 WorkItem 계획(JSON 스키마)**만 만들고
  - **Router가 selector(tags/capabilities)로 타겟을 자동 매칭**한다
- 멀티 타겟 작업을 병렬/순차로 실행하며 상태를 추적

### 핵심 개념
- WorkItem:
  - id/title/playbook_id/inputs/selector/depends_on
- Router:
  - selector(tags_any, tags_all, role, capabilities)로 best-fit target 선택
- Orchestrator:
  - target별 queue 생성
  - 의존성 충족 후 실행
  - 상태(PENDING/RUNNING/DONE/FAILED) 기록

### API 제안(최소)
- `POST /projects/{id}/plan` : WorkItem plan 저장
- `POST /projects/{id}/dispatch_plan` : 자동 배분 + 실행 시작(또는 한 번에)
- `GET /projects/{id}/plan` : plan 조회

### 완료 기준
- “서버1 suricata / 서버2 opnsense / 서버3 waf+dvwa” 같은 요청을
  - WorkItems로 분해
  - Router가 자동 배분
  - 각 타겟 subagent에서 실행
  - 전체 진행 상황이 project state에 남는다

---

## M3-4.4 Execution Profile 분리 (진단 vs 설치)
### 목표
- 현재 M3-3 sanitize 정책은 “진단/검증”에 최적화되어 있어 설치 작업에 부적합
- 따라서 **작업 유형별 실행 정책(execution_profile)**을 분리한다

### 예시
- `container-safe`:
  - sudo/systemctl 금지
  - 진단용
- `remote-install`:
  - sudo 허용(필요)
  - 위험 명령(rm -rf /, mkfs, dd 등)만 금지
  - approver/admin 권한 + 감사 강화 필수

### 완료 기준
- Suricata/ModSecurity 같은 설치 플레이북에서 sudo/systemctl이 drop되지 않는다
- 대신 위험 커맨드만 필터링된다

---

## M3-4.5 Dashboard/Progress (체감 완성)
### 목표
- “산으로 간 느낌”을 없애는 가장 큰 요소는 **진행률/마일스톤 가시화**
- 최소 대시보드를 만들어 “지금 어디까지 됐는지”가 보이게 한다

### 범위(최소)
- ProjectState에:
  - `work_items_status` (각 WorkItem 상태)
  - `current_milestone`, `progress_percent`
  - 최근 실패 원인/다음 액션
- Web UI:
  - 프로젝트 화면에 WorkItem 목록/상태/최근 로그 요약
  - Evidence/Report 다운로드 링크

### 완료 기준
- 사용자는 “작업이 분산되어 진행 중/완료/실패”를 한 화면에서 확인 가능

---

# 4) 수정된 M3-4 실행 순서 (회귀 최소/체감 최대)

1) **M3-4.1 Targets Registry** (원격 라우팅 체감 시작)
2) **M3-4.2 Playbook Runner** (절차 기반 실행 체감)
3) **M3-4.4 Execution Profile 분리** (설치 작업 가능 상태)
4) **M3-4.3 WorkItem Plan + Router** (자동 배분/멀티타겟)
5) **M3-4.5 Dashboard/Progress** (진행상황 체감 완성)

> 이유: 타겟/실행/정책이 먼저 안정화되어야 “자동 배분”을 붙여도 안전하다.

---

# 5) 산출물(깃 반영 문서/코드)

## 문서
- `docs/M3-PLAN.md` (본 문서)
- `docs/M3-4-TARGETS.md`
- `docs/M3-4-PLAYBOOKS.md`
- `docs/M3-4-WORKITEMS.md`
- `docs/M3-4-EXECUTION-PROFILES.md`
- `docs/M3-4-DASHBOARD.md`

## 코드(예상)
- `api/targets_store.py`
- `api/playbook_store.py`
- `api/rag_store.py` (이미 MVP)
- `api/workflows/playbook_runner.py`
- `api/workflows/plan_router.py` (WorkItem selector → target 매칭)
- `api/main.py` 엔드포인트 확장
- `web/` 대시보드 UI 개선

---

## 6) 체크포인트(“산으로 가지 않게” 확인하는 기준)
- 외부 마스터 호출은 항상 MasterGate 승인 큐를 통과한다 ✅
- 실행은 target_id 기반으로 subagent로 라우팅된다 ✅
- WorkItem 상태가 project state/audit에 남는다 ✅
- 대시보드에서 진행률을 볼 수 있다 ✅

---

이 문서 기준으로 M3-4를 진행하면,
“진단 도구처럼 보이던 OpsClaw”가 “진짜 분산 오케스트레이션 플랫폼”처럼 동작하게 된다.