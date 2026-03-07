```md
# Skills.md — OpsClaw Skill System (Hybrid: Dynamic Master + Reusable Skills)

작성일: 2026-03-06  
대상: OpsClaw (Manager + SubAgent + Master LLM)  
목표: “완전 동적(즉석) 실행”의 장점은 유지하면서, 반복/고위험 작업은 **Skill로 캡슐화**해 안정성/정확도/재현성을 끌어올린다.

---

## 0) 한 줄 정의

**Skill = “입력/출력 계약 + 실행(도구/명령/API) + 검증 + 증빙 + 정책(승인/제한)”을 한 번에 묶은 재사용 단위.**

- Master(LLM)는 매번 동적으로 “무엇을 할지” 결정한다.
- 하지만 **반복적이거나 위험한 실행은 Skill로 호출**한다.
- Manager는 Skill 실행을 오케스트레이션하고 증빙/감사를 남긴다.
- SubAgent는 실제 실행(쉘/HTTP/도구/스크립트)을 담당한다.

---

## 1) 왜 Skill이 필요한가

### 1.1 완전 동적(LLM 즉석 실행)만으로는 불리한 점
- **재현성 부족**: 매번 명령/순서/출력이 달라진다.
- **안전성 위험**: 잘못된 명령이 “즉시 실행”될 수 있다.
- **품질 편차**: 모델 컨디션/컨텍스트/프롬프트에 따라 결과가 흔들린다.
- **비용/속도**: 매번 도구 탐색/학습/결정을 LLM이 하면 토큰/시간이 증가한다.

### 1.2 Skill의 이점
- **정확도/안정성**: 검증된 절차를 캡슐화(입출력 고정 + 검증 규칙)
- **통제(Policy)**: 고위험 작업에 승인/차단/롤백을 내장
- **증빙(Evidence)**: 결과/로그/아티팩트 수집이 자동
- **누적 학습**: 한 번 잘 된 흐름을 “재사용 자산”으로 축적

---

## 2) OpsClaw에서의 Skill 철학 (Hybrid Model)

OpsClaw는 두 레이어가 동시에 존재한다.

### 2.1 Dynamic Layer (Master-driven)
- Master가 상황에 맞게 **Probe(확인) → Decide(결정) → Act(실행)**를 설계한다.
- 도구가 없으면 **검색→clone→문서학습→실행→랩핑(API화)**도 설계한다.
- 모호하면 질문을 최소화하고, 가능한 한 probe로 해결한다.

### 2.2 Skill Layer (Reusable, controlled execution)
- 반복적/고위험/운영 표준화 영역은 Skill로 실행한다.
- Master는 “Skill을 선택/조합”하거나 “새 Skill로 승격할지”를 결정한다.
- Skill 실행은 항상 Manager/SubAgent의 통제(감사/증빙) 아래에서 이뤄진다.

---

## 3) Skill의 종류(권장 분류)

### 3.1 Primitive Skills (기본 실행 빌딩블록)
- `shell.run` : 멀티라인 bash script 실행
- `http.request` : HTTP 호출(curl/requests)
- `file.collect` : 파일/디렉토리 증빙 수집
- `archive.pack` : 결과 ZIP 패키징

> Primitive는 “모든 것의 기반”.  
> 가능한 한 SubAgent 기본 기능으로 제공.

### 3.2 Observation Skills (진단/관측)
- `sys.probe` : OS/CPU/MEM/DISK/PROC 기본 수집
- `net.probe` : NIC/ADDR/ROUTE/DNS/REACHABILITY 수집
- `svc.probe` : 포트 리슨/헬스 엔드포인트/프로세스 상태

> “ens33/ens34” 같은 이슈는 특정 제품이 아니라 **net.probe 도메인**으로 흡수된다.

### 3.3 High-Risk Skills (승인/롤백 포함)
- `fw.apply_ruleset` : 방화벽 룰 적용(드라이런/롤백/승인)
- `pkg.install` : 패키지 설치/업그레이드(정책/승인)
- `deploy.compose` : 서비스 배포/재기동(롤백)

### 3.4 Tool Lifecycle Skills (OSS 도구 활용)
- `tool.discover` : 웹/GitHub 검색(후보 리스트)
- `tool.acquire` : clone/다운로드 + 버전 고정
- `tool.understand` : README/--help에서 사용법 추출(요약 + 예제 명령)
- `tool.run` : 실행 + 결과 수집
- `tool.wrap` : wrapper/API 생성(입출력 통제)

> “없으면 찾고, 문서 읽고, 목적 맞게 실행”은 **Tool Lifecycle Skill 체계**로 표준화한다.

---

## 4) Skill의 계약(Contract): 입력/출력/정책/증빙

Skill이 “코드 하드코딩”이 되지 않으려면, 아래 항목을 **스펙으로 분리**해야 한다.

### 4.1 입력(Input)
- JSON schema로 선언(필수/선택/타입/범위)
- 민감 정보(secrets)는 별도 채널(환경변수/보안 저장소)로 분리

### 4.2 출력(Output)
- 최소 표준:
  - `ok` (bool)
  - `data` (dict/array/str)
  - `exit_code` (shell일 때)
  - `logs` (stdout/stderr 요약)
  - `artifacts` (파일 경로 목록)
  - `evidence_refs` (SubAgent evidence refs)

### 4.3 정책(Policy)
- `risk: low|medium|high`
- `approval_required: bool`
- `deny_commands` / `allow_patterns`
- 실행 타겟 제한(어느 target tag에서만 가능 등)

### 4.4 증빙(Evidence)
- 실행 명령/응답 원문
- 출력 로그(stdout/stderr)
- 생성 파일/리포트
- 버전 정보(도구 커밋/태그/sha)

---

## 5) Skill 표현 형식(권장)

### 5.1 YAML은 “작업 언어”가 아니라 “입출력 통제/정책/증빙 계약” 용도
- YAML을 사용해도 좋다. 단, YAML은 **Contract/Metadata** 위주로 쓴다.
- 실행 절차 자체는 playbook(IR) 또는 wrapper 코드로 구현될 수 있다.

권장 파일 구조:
```

skills/
net.probe/
skill.yaml
README.md
runner.sh (optional)
wrapper/ (optional)
tool.lifecycle/
skill.yaml
README.md

````

### 5.2 skill.yaml 예시(개념)
```yaml
id: net.probe
version: 0.1
risk: low
approval_required: false

inputs:
  type: object
  properties:
    target_id: { type: string }
  required: [target_id]

outputs:
  type: object
  properties:
    ok: { type: boolean }
    data: { type: object }
    artifacts: { type: array, items: { type: string } }

evidence:
  collect:
    - stdout
    - stderr
  max_kb: 512
````

---

## 6) 실행 모델 (Skill 호출이 실제로 어떻게 동작하나)

### 6.1 실행 주체

* **Manager**: Skill 선택/스케줄링/정책 적용/감사 기록
* **SubAgent**: 실행(쉘/HTTP/도구) + evidence 생성
* **Master(LLM)**: “Skill 선택/파라미터 생성/다음 행동 결정”

### 6.2 실행 플로우(표준)

1. User request → project 생성
2. Manager가 Master에게:

   * “이 목표에 필요한 Skill/Probe/Plan을 생성해라”
3. Master가:

   * (a) 기존 Skill 호출 계획 생성 또는
   * (b) Tool lifecycle 수행 계획 생성 또는
   * (c) 질문 최소화(필요 시)
4. Manager가 Skill/Probe를 SubAgent로 실행
5. 결과를 state/audit/evidence에 저장
6. Master가 결과로 재계획/결정
7. 목표 달성 시 evidence pack 생성

---

## 7) “Skill을 언제 만들고, 언제 동적으로만 처리하나?”

### 7.1 Skill로 승격(모듈화)해야 하는 기준

* 동일/유사 작업이 **반복**될 때
* 실수 비용이 큰 **고위험 작업**일 때
* 결과 형식을 **항상 동일하게** 만들 필요가 있을 때(리포트/대시보드/감사)

### 7.2 동적 처리만으로 충분한 경우

* 일회성 조사/탐색/분석(“지금 무슨 일이야?”)
* 아직 문제 공간이 불확실해서 표준화가 의미 없는 경우

### 7.3 가장 좋은 운영 방식(추천)

* 처음에는 Master가 동적으로 해결한다.
* 해결 과정(Probe/Act/Validate) 중 “안정적으로 반복 가능한 흐름”이 나타나면:

  * Manager가 “draft skill/playbook”으로 저장(승격)
* 이후엔 skill 우선 사용 → 실패 시 동적 루프로 폴백

---

## 8) Skill과 “도구(OSS) 활용”의 관계

OpsClaw의 Skill은 “내장 기능”만 말하는 게 아니다.

* **외부 CLI/오픈소스 도구 자체가 Skill의 구현**이 될 수 있다.
* 핵심은 “입출력 통제 + 증빙 + 정책”을 OpsClaw가 잡는 것.

### 8.1 도구가 없으면?

Master가 Tool Lifecycle을 수행:

* discover → acquire → understand → probe → execute → (필요 시 wrap)

### 8.2 wrap(API화)이 필요한 경우

* 출력이 비정형/불안정해서 파이프라인으로 쓰기 힘듦
* 동일 도구를 여러 작업에서 재사용해야 함
* 결과를 state에 구조화해서 저장해야 함

---

## 9) LLM(모델)과 Skill의 연결 (Role Binding)

OpsClaw는 LLM을 역할별로 선택 가능:

* master_conn_id: 계획/결정/재계획
* manager_conn_id: 요약/리포트(선택)
* subagent_default_conn_id: 로컬 자동화(선택)

원칙:

* 실행은 SubAgent가 한다.
* LLM은 “무엇을 실행할지”를 만든다.
* 모든 실행은 audit/evidence로 남는다.

---

## 10) M3-5.2와 Skill 시스템의 관계 (지금 단계)

M3-5.2의 핵심은:

* input_resolver 같은 “규칙 없는 자동선택”을 없애고
* Master가 동적으로 probe를 설계/실행하여 inputs/plan을 확정하는 루프를 만든다.

이 루프가 안정화되면,

* 그 과정에서 반복되는 흐름이 자연스럽게 Skill로 승격된다.

---

## 11) TODO (Skill 시스템 완성까지)

### v0 (즉시)

* Master-guided Probe Loop 확립(추측 금지, 증거 기반 결정)
* Skill contract(입출력/정책/증빙) 문서화 및 기본 템플릿 제공

### v1

* Skill registry(목록/검색/버전 관리)
* Skill runner(Manager가 skill.yaml 기반으로 실행)
* High-risk 승인/롤백/드라이런 표준화

### v2

* Tool lifecycle + wrapper 자동 생성 파이프라인
* “동적 실행 → 검증 → skill 승격” 자동화(semiauto)

---

## 12) 핵심 원칙(반드시 유지)

* **OpsClaw는 특정 제품 설치기가 아니라 범용 시스템 제어 오케스트레이터다.**
* **추측하지 않는다.** 필요한 정보는 probe로 확인한다.
* **사람은 최소로만** 개입한다(고위험/모호한 선택).
* **증빙/감사/재현**은 기본값이다.

```

원하면, 이 `Skills.md`를 기준으로 바로 다음 문서도 같이 만들어줄게:

- `SkillContract.yaml` 템플릿(입출력/정책/증빙 고정 스키마)
- `SkillLifecycle.md` (동적 실행 → 검증 → skill 승격 프로세스)
- `ToolLifecycle.md` (discover/acquire/understand/run/wrap 상세)
```
