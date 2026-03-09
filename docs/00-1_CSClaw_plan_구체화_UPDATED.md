# ChassisClaw 확정 계획서 v3

## 0. 이 문서의 목적

이 문서는 새 채팅에서 ChassisClaw 개발을 이어가기 위한 **최신 기준 문서**다.  
이전 문서들에서 유효한 핵심 개념은 유지하되, 현재까지의 설계 변경과 구현 경험을 반영해 다음 세 가지를 명확히 고정한다.

1. ChassisClaw는 **Tool-driven execution loop system**이다.  
2. 관리의 기준점은 `target`이 아니라 **asset**이다.  
3. 현재 개발 상태는 **M1 완료, M2 완료, M3 진행 중**이다.

---

## 1. 최종 제품 정의

ChassisClaw는 LangGraph와 A2A를 뼈대로 하는 **AI 에이전트 오케스트레이션 시스템**이다. 사용자는 자연어로 목표를 주고, Master가 상위 판단과 검수를 담당하며, Manager가 상태기계와 정책, Playbook, 재계획을 운영하고, SubAgent가 대상 시스템에서 Tool을 사용해 실제 실행과 증빙 수집을 담당한다.

핵심은 아래 한 줄로 정리된다.

> **ChassisClaw는 Agent가 Tool(OS 명령어, 동적 쉘 스크립트, OSS 설치·실행, wrapper 생성)을 사용하고 그 stdout/stderr/evidence를 다시 읽어 다음 계획을 세우는 실행 루프 시스템이다.**

즉 ChassisClaw는 단순 대화형 비서나 정적 플레이북 실행기가 아니라,

- 계획하고,
- 확인하고,
- 실행하고,
- 검증하고,
- 실패하면 다시 계획하는

**폐루프 실행 시스템**이다.

---

## 2. 핵심 철학

### 2.1 Tool-first Execution

실제 일은 Tool이 한다. LLM은 Tool을 언제, 어디서, 어떤 순서와 입력으로 사용할지 정한다.  
구조는 다음과 같다.

**LLM이 계획 → Tool이 실행 → evidence 생성 → LLM이 재판단**

### 2.2 Evidence-first

모든 Tool 실행은 반드시 아래를 남긴다.

- 실행 명령 또는 실행 payload
- stdout / stderr
- exit code
- 생성 파일 및 산출물
- 사용한 OSS 버전/커밋/태그
- evidence refs

### 2.3 Human-minimized but not human-eliminated

probe만으로 확정하기 어려운 값은 질문해야 한다.  
예:

- 내부망 CIDR 범위
- 인터페이스 naming 기준
- 로그 보관 기간
- 재시작 허용 여부
- 고위험 변경 승인

### 2.4 YAML-first가 아니라 IR-first

YAML은 입력/메타데이터/계약 표현에 사용할 수 있으나, 최종 실행 표준은 **IR(JSON 중간표현)** 이다.  
자연어, YAML, LLM 출력은 모두 IR로 정규화되어 실행된다.

### 2.5 Asset-first Management

이전 설계의 가장 큰 문제는 `target`에 너무 많은 의미를 몰아넣은 것이다. 이제 기준을 아래처럼 고정한다.

- **Asset**: ChassisClaw가 관리하는 자산 그 자체
- **Agent/SubAgent**: asset 위에서 실행을 담당하는 인터페이스
- **Target**: 특정 작업 시점에 asset으로부터 파생된 실행 단위

즉,

**등록은 asset 기준으로 하고, 실행 시점에 target으로 resolve한다.**

---

## 3. 핵심 개념 체계

## 3.1 Asset

관리 대상의 기본 단위다.

예:

- 서버
- VM
- 컨테이너 호스트
- 네트워크 장비
- 특정 관리 서비스 인스턴스

Asset는 다음을 가진다.

- 식별자
- 주소/접속 정보
- 플랫폼/태그
- 상태
- 연결된 subagent 정보
- capability 정보
- 운영 메타데이터

## 3.2 Agent / SubAgent

Asset 위에서 실제 실행과 probe를 담당한다.

역할:

- `/health`
- `/capabilities`
- `run_script`
- `push_file`
- `pull_file`
- evidence 수집

중요한 점은 **agent는 asset에 종속**된다는 것이다.

## 3.3 Target

Target은 영구 저장 중심 엔티티가 아니라 **특정 run에서 해석된 실행 대상**이다.

예:

- asset `vm-143`가 현재 run에서 `node_a` 역할의 target이 됨
- asset `vm-144`가 현재 run에서 `node_b` 역할의 target이 됨

## 3.4 Tool

실제 액션의 최소 실행 단위다.

예:

- shell exec
- http probe
- file op
- apt install
- service restart
- GitHub clone 후 OSS 실행

## 3.5 Skill

Tool 사용을 통제된 계약으로 감싼 재사용 단위다.

예:

- `sys.probe`
- `net.probe`
- `svc.probe`
- `tool.lifecycle`
- `ops.onboard.two_node`

## 3.6 Playbook

여러 Skill과 Tool, 질문, 승인, 검증 단계를 묶은 실행 청사진이다.  
정적 YAML 저장소가 아니라, 다음을 모두 포함한다.

- 템플릿 기반 초안
- LLM 동적 생성 초안
- 실행 중 probe 결과 기반 수정
- 반복 작업의 정식 승격

## 3.7 Experience

성공/실패 패턴, remediation, 승인 이력, 조직 선호 등을 저장하는 운영 경험층이다.  
단, 사용자 의도나 정책 확정을 대체하지 않는다.

## 3.8 Organization Profile

조직의 운영 기준을 저장한다.

예:

- 내부망/외부망 CIDR
- 허용 도구/금지 도구
- 로그 보관 기준
- 승인 규칙
- sudo/ssh/subagent 정책

---

## 4. 시스템 역할

### 4.1 Master

- 사용자 목표 해석
- 동적 Playbook 초안 생성
- Tool/Skill 후보 전략 수립
- 질문 최소화
- 실패 시 재계획
- 완료 후 검수

### 4.2 Manager

- LangGraph workflow 실행
- state / audit / evidence / artifact 저장
- Playbook IR 관리
- Tool/Skill orchestration
- A2A fan-out / fan-in
- 질문/승인 처리

### 4.3 SubAgent

- 실제 대상 시스템에서 Tool 실행
- stdout/stderr/artifact/evidence 수집
- capability probe 수행

---

## 5. 표준 실행 사이클

ChassisClaw는 아래 상태기계를 따른다.

1. **Plan**  
   목표, 대상, unknowns, constraints, validation 기준 정리

2. **Probe**  
   필요한 unknown을 최소 명령으로 확인

3. **Resolve**  
   결정 방식 분기
   - AUTO
   - CONFIRM
   - ASK
   - APPROVAL

4. **Execute**  
   선택된 Skill/Tool sequence 실행

5. **Validate**  
   목표 달성 여부 검증

6. **Replan**  
   실패 시 stderr/evidence 기반 수정 계획 생성

7. **Report**  
   요약 보고서와 evidence pack 생성

---

## 6. Tool Lifecycle을 코어 기능으로 채택

ChassisClaw는 기존 Tool만 쓰는 시스템이 아니다. 필요한 Tool이 없으면 OSS를 스스로 도입한다.

표준 단계:

1. Discover
2. Acquire
3. Understand
4. Probe
5. Execute
6. Record

즉,

> **없으면 찾고, 받고, 읽고, 시험하고, 실행하고, 기록한다.**

---

## 7. 현재 기준 레포 구성 방향

최상위는 다음 4개 프로그램 중심으로 고정한다.

- `core/` : 권위 있는 컨트롤 플레인
- `subagent/` : 대상 시스템 실행면
- `engine/` : 선택적 실행 엔진(NanoClaw 등)
- `bootstrap/` : 초기 온보딩 전용

추가로 데이터/계약 계층은 다음을 가진다.

- `skills/`
- `playbooks/`
- `org_profiles/`
- `data/state/assets/`
- `data/state/targets/` (필요 시 캐시 또는 파생 정보)

---

## 8. 현재까지 구현 상태

### 완료

- **M1 완료**: 프로젝트 상태 저장, run_auto 골격, answer/approve, validation/replan 최소 루프, skill registry, 대표 skill stub
- **M2 완료**: `ops.onboard.two_node` 기준으로 precheck → probe → decision → approval → install stub → report 흐름 연결, failure modeling, identity mismatch 검출

### 진행 중

- **M3 진행 중**: asset 중심 구조로 전환 중

현재 핵심 미완료 사항:

- remote VM 2대를 진짜 asset으로 등록하는 흐름
- asset 기반 onboarding skill
- target을 asset에서 파생하는 구조
- local-agent 테스트 잔재 제거

---

## 9. 현재 가장 중요한 설계 확정사항

### 9.1 더 이상 local-agent 테스트 seed에 오래 의존하지 않는다

`local-agent-1`, `local-agent-2`가 같은 endpoint를 바라보는 구조는 이제 개발 편의용 임시 상태로만 취급한다.

### 9.2 진짜 원격 VM 2대가 M3 기준이다

현재 기준 실전 구조는 다음과 같다.

- remote VM 1
- remote VM 2
- 각 VM에 subagent 설치
- 각 VM이 서로 다른 agent identity를 반환
- Manager가 이를 asset registry에 등록

### 9.3 onboarding의 산출물은 target이 아니라 asset 등록이다

처음 온보딩의 산출물은 “target 생성”이 아니라,

- asset 등록/갱신
- asset-agent 매핑 저장
- capability 반영

이다.

---

## 10. M3 목표

M3의 목표는 다음 4개다.

1. **Remote SubAgent Bootstrap**
2. **Asset Registry 도입**
3. **Asset → Target Resolve 분리**
4. **ops.onboard.two_node의 asset 기반 재구성**

### M3 완료조건

- 원격 VM 2대에 각각 subagent가 올라감
- 각 subagent가 서로 다른 `agent_id`를 반환함
- manager가 두 원격 시스템을 asset으로 등록함
- skill이 asset 기준으로 입력을 받거나 내부에서 asset을 조회함
- 실행 시 각 asset이 target으로 올바르게 resolve됨
- identity mismatch 없이 summary가 생성됨

---

## 11. 최종 한 줄 정의

> **ChassisClaw는 asset을 중심으로 관리하고, 요청 시 asset을 target으로 resolve하여, Agent가 Tool을 사용해 실제 환경을 바꾸고 그 stdout/stderr/evidence를 다시 읽어 다음 계획을 세우는 LangGraph+A2A 기반 AI 에이전트 오케스트레이션 시스템이다.**
