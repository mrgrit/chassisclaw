아래는 **지금까지 대화에서 나온 핵심(도구/스킬/웹검색/clone/문서학습/랩핑/API화/IR/LLM probe loop/최소 human 질문/증빙)** 을 전부 포함해서 다시 쓴 **최종 비전 로드맵 + 마일스톤 + 사용자 케이스 12개**야.

---

# 1) 최종 비전 한 줄 정의

**사용자는 자연어로 목표만 말한다 → LLM이 필요한 “확인(Probe)”을 설계/실행하고 → 증거 기반으로 계획을 만들고 → 도구/CLI/웹 기반 OSS를 찾아/설치/학습/실행/랩핑(API화)까지 하며 → 검증/오류해결/재계획을 반복해 목표를 달성한다.**
(사람은 모호하거나 위험한 결정만 최소로 승인/선택)

---

# 2) 개발 계획 / 마일스톤 (비전 달성까지)

## M4-0 IR(중간표현) v0 확정

**목표:** YAML/자연어/LLM 생성물/도구 실행을 모두 “하나의 실행 표준(IR JSON)”으로 통일
**산출물**

* IR 스키마 v0

  * `goal`, `context`, `constraints/policy`
  * `unknowns`, `probes`, `evidence`
  * `decisions`, `plan`(jobs/steps), `validate`
  * `errors`, `fixes`, `replans`, `iterations`
* state에 `plan_ir`, `run_ir`, `evidence_index` 저장
* audit 이벤트 타입 표준화(PLAN/PROBE/DECIDE/EXEC/VALIDATE)

**완료조건**

* 같은 IR로 재실행 시 결과 재현 가능
* 모든 실행에 evidence/audit가 자동 남음

---

## M4-1 LLM Probe Loop v0 (확인→결정→최소 질문)

**목표:** LLM이 “추측”이 아니라 **확인 명령(probe) 실행 결과**로 판단
**산출물**

* `probe_planner`: unknown/모호성을 해결하기 위한 probes(IR.probes) 생성
* `probe_runner`: SubAgent로 probes 실행 + evidence 저장
* `decider`: evidence 기반 결정(decisions) 생성
* `human_min_questions`: ambiguity/higher-risk일 때만 choices+질문 생성

**완료조건**

* “인터페이스 선택, 서비스명 결정, 경로/설정 위치 탐색” 같은 입력이

  * probe→결정으로 자동 해결되거나,
  * 필요한 경우에만 최소 질문으로 멈춤

---

## M4-2 Tool Lifecycle Engine v0 (OSS 도구 활용 엔진)

**목표:** “없으면 찾고/clone하고/문서학습해서/목적에 맞게 실행”하는 도구 활용 파이프라인
**산출물(표준 단계)**

1. **Discover**: 웹/GitHub 검색으로 후보 수집
2. **Acquire**: clone/download + 버전 고정(태그/커밋)
3. **Understand**: README/--help/예제에서 사용법 추출(LLM 요약)
4. **Probe**: dry-run/샘플 입력으로 실행성 검증
5. **Execute**: 목적 달성 명령 실행 + 결과 수집
6. **Record**: 사용법/명령/버전/출력 포맷을 IR에 저장(재사용)

**완료조건**

* “신규 OSS 도구 1개”를 목표 기반으로 자동 도입→실행→증빙까지 완주
* 도구 버전/명령/출력/파일이 evidence로 남아 재현 가능

---

## M4-3 Wrapper/API화 Engine v0 (입출력 통제)

**목표:** 도구가 CLI만 제공해도, 필요 시 자동으로 **I/O 통제 가능한 래퍼(API/CLI wrapper)** 생성
**산출물**

* wrapper 템플릿(고정)

  * 입력 JSON → 실행 → 출력 JSON
  * `{ok, data, logs, artifacts, exit_code}`
* “도구별 wrapper 생성/업데이트” 절차를 IR로 저장
* wrapper 등록(재사용 가능)

**완료조건**

* 기존 CLI 도구 1개를 선택해 wrapper 생성 후,

  * OpsClaw가 항상 JSON으로 입력/출력을 제어 가능

---

## M4-4 Skill Package v0 (재사용 단위)

**목표:** Skill = “특정 목적 달성에 검증된 도구+절차+입출력 계약”을 패키징하여 재사용
**산출물**

* Skill은 “고정 커맨드 목록”이 아니라:

  * **Tool lifecycle 결과물 + wrapper + 검증 규칙 + 정책**의 묶음
* YAML은 여기서 유효:

  * “입력/출력 계약(스키마), 정책, 위험도, 증빙 규칙”을 선언하는 용도

**완료조건**

* 자주 쓰는 10개 업무가 “skill로 등록”되어 재사용 가능
* LLM은 필요 시 “skill 재사용 vs 새로운 tool lifecycle 수행”을 결정

---

## M4-5 Orchestrator Loop v1 (Plan→Exec→Validate→Fix→Replan)

**목표:** 최종 루프 엔진(네가 말한 핵심) 완성
**산출물**

* 반복 루프:

  1. 목표 이해/제약 반영
  2. unknowns 정리
  3. probe 실행
  4. 결정
  5. 실행
  6. 검증
  7. 실패 시 진단/수정/재계획
* 반복 상한/중단/승인 게이트(policy)

**완료조건**

* 실패 유도 시나리오 5개에서 자동 복구(replan)가 동작
* 위험 작업은 승인 없이 실행되지 않음

---

## M4-6 Evidence Pack v1 (원격 포함, 제출 가능)

**목표:** 모든 작업이 “감사/제출 가능한 증빙 패키지”로 자동 정리
**산출물**

* 원격 evidence pull
* 프로젝트 ZIP:

  * IR snapshot, audit.jsonl, probe logs, 실행 로그, 산출물, tool versions, wrapper code

**완료조건**

* 멀티 타겟 실행의 원격 결과가 ZIP에 포함

---

## M4-7 UX(Console) v1

**목표:** 사용자가 자연어로 지휘하고, 질문/승인/선택을 UI로 최소 수행
**산출물**

* 진행 상태: PLAN/PROBE/DECIDE/EXEC/VALIDATE 타임라인
* 질문/선택/승인 UI
* 도구 도입/학습 과정 가시화(어떤 OSS를 왜 골랐는지)

**완료조건**

* 비개발자도 10분 안에 3개 업무 수행 + 증빙 ZIP 생성

---

# 3) 완료된 시스템 사용자 케이스 12개 (도구/스킬/OSS 포함)

## 1) “원인 모르는 장애” 자동 진단/복구

* “웹이 느려졌어. 원인 찾고 복구해”
* LLM probe: CPU/mem/disk/net + 로그
* 결정: 병목 특정 → 도구(예: flamegraph/pprof 등) 필요하면 OSS 찾고 도입
* 실행/검증/재계획 반복

## 2) “서버 전체 보안 점검” (OSS 스캐너 도입 포함)

* “취약 설정/열린 포트/취약 패키지 점검해서 보고서 만들어”
* 필요하면 OSS 스캐너를 Discover→Acquire→Understand 후 실행
* 결과를 wrapper로 정형화해 리포트+evidence zip 생성

## 3) “로그 원인 분석” + 도구 자동 활용

* “인증 실패가 급증했어. 원인과 공격 패턴 알려줘”
* probe: auth.log, sshd config, IP 집계
* 필요하면 log 분석 OSS 도구 도입
* 증빙과 결론을 함께 저장

## 4) “네트워크 구성 파악” (LLM probe로 NIC/route 결정)

* “이 서버 네트워크 구조 정리하고 인/아웃 인터페이스 구분해”
* LLM이 probe 명령 설계→실행→ens33/ens34 같은 결론 도출
* 애매하면 최소 질문

## 5) “클러스터 롤링 업데이트” (DAG 실행 + 검증)

* “노드 5대 롤링 업데이트, 다운타임 최소화”
* IR DAG 생성, 실패 시 해당 노드만 fix/retry
* evidence pack 자동 생성

## 6) “방화벽 정책 변경” (승인 게이트 + 검증)

* “특정 서비스 포트만 허용하도록 변경”
* 위험도 high → human 승인 요구
* 적용 후 validate(접속 테스트) + 롤백 플랜 포함

## 7) “도구가 없는 작업”을 OSS로 해결

* “PCAP에서 특정 트래픽 패턴 찾아”
* 해당 목적의 OSS를 검색/클론/사용법 학습 후 실행
* 필요 시 wrapper로 I/O 통제하여 파이프라인화

## 8) “DB 백업/복구 리허설” (증빙 중심)

* “백업 정책 점검하고 복구 리허설까지 해서 증빙 남겨”
* probe→exec→validate
* 결과/로그/스크립트가 zip에 포함

## 9) “권한/IAM 감사”

* “과도한 권한 계정 찾아서 정리안 만들고 적용(승인 필요)”
* probe: 사용자/권한 수집 도구 활용
* 결정: 위험 권한 후보 제시 → 승인 후 적용

## 10) “성능 튜닝” (실험/검증 반복)

* “API p95 튀어. 원인 찾고 개선”
* LLM이 probe(메트릭/로그)→가설→변경→검증 반복
* 필요 도구(벤치마크/프로파일러) 자동 도입

## 11) “보안 이벤트 대응” (격리/조사/복구)

* “이상 트래픽. 감염 조사하고 격리”
* high-risk 조치(격리/차단)는 승인 필요
* 조사 도구/스크립트는 OSS 활용 + evidence 저장

## 12) “운영 리포트 자동 생성”

* “이번 주 변경/장애/조치/증빙 ZIP까지 정리”
* audit/evidence/IR 기반 자동 요약 + 제출용 패키징