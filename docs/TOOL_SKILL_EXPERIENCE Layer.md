좋다.
그 방향이 맞다. **`Tool / Skill / Experience` 3층 구조**로 가자.

그리고 방금 결과에서 하나 먼저 짚으면, 지금 `inputs`는 잘 채워졌는데 `input_rationales`와 `evidence_map`가 비어 있다. 이건 `sys.probe` 방향 논의와 별개로, 다음에 `run_auto`에서 한 번 더 잡아야 하는 작은 회귀다. 기능 자체는 되는데, 메타가 최종 plan에 안 실리는 구간이 있는 상태로 보인다.

## 내가 보는 최종 구조

### 1. Tool

가장 아래층이다.
실행 수단 그 자체다.

예:

* shell.run
* http.request
* file.collect
* archive.pack
* 외부 OSS CLI
* 브라우저 자동화 도구
* 메일 API/IMAP/Graph/Gmail connector

이건 “손발”이다. Skills 문서의 Primitive Skills와 Tool Lifecycle이 여기에 해당한다. 문서도 Primitive를 모든 것의 기반으로 보고, 도구가 없으면 discover → acquire → understand → probe → execute → wrap의 lifecycle로 다루라고 정리한다.

### 2. Skill

도구를 **입출력 통제 + 정책 + 증빙** 아래 묶은 재사용 단위다.

예:

* sys.probe
* net.probe
* svc.probe
* fs.probe
* fw.apply_ruleset
* pkg.install
* deploy.compose
* mail.read
* mail.reply_draft
* mail.delete

이건 “검증된 기술”이다. 문서에서도 Skill은 재현성, 안전성, 정책 통제, 증빙, 재사용 자산 축적을 위한 계층이고, 반복적/고위험/출력 표준화가 필요한 작업에 승격하라고 되어 있다.

### 3. Experience

이게 네가 방금 짚은 핵심이다.
사용자의 과거 결정, 조직의 선호, 이전 성공/실패 사례, 승인 패턴, 환경별 관습, “이럴 때 보통 이렇게 했다”를 축적하는 층이다.

예:

* 이 조직은 Debian 계열이면 `apt`와 `systemd` 조합이 일반적
* 이 타겟 그룹은 방화벽 룰 적용 전에 꼭 dry-run을 선호
* 이 사용자는 자동 삭제보다 trash 이동을 선호
* 이 네트워크 대역에선 inline in/out 선택 시 ens37↔ens38 조합이 반복됨
* 이 서비스 장애에서 CPU보다 DB connection 고갈이 더 자주 원인이었음
* 이 메일 발신자 도메인은 항상 low-priority 분류됨

이건 “기억과 경험”이다.
현재 문서엔 Experience라는 이름은 직접 안 박혀 있지만, Skill 문서가 “한 번 잘 된 흐름을 재사용 자산으로 축적”해야 한다고 하고, 장기 로드맵도 IR/state/evidence를 저장해 같은 실행을 재현 가능하게 하라고 한다. 그걸 한 단계 더 올리면 Experience 층이 된다.

## 왜 Experience가 필요한가

현재 Tool만 있으면 매번 원시 실행만 한다.
Skill까지 있으면 “잘 정의된 재사용 작업”은 안정적으로 한다.

하지만 여전히 빠지는 게 있다.

* 사용자/조직마다 선호가 다름
* 환경마다 반복되는 패턴이 다름
* 이전에 사람에게 물어본 결정들이 다시 나오기도 함
* 같은 문제라도 “이 조직에서 허용되는 방식”이 다름

이걸 매번 모델이 처음부터 추론하게 하면 비효율적이고 흔들린다.
그래서 Experience는 필요하다.

**사람이 한 결정과, 시스템이 검증해 본 결과를 미래 의사결정에 반영하는 층**이 있어야 한다.

## Experience에는 뭘 저장하나

여기서 중요한 건 그냥 대화 로그를 다 저장하는 게 아니다.
“나중에 의사결정에 재사용 가능한 단위”만 구조화해서 저장해야 한다.

나는 최소 5종으로 나누는 게 좋다고 본다.

### A. Preference

사용자/조직 선호

예:

* 자동 삭제보다 휴지통 선호
* 외부 발신 자동답장은 초안만 생성
* 고위험 변경은 항상 승인 요구
* 장애 복구 시 재시작보다 상태 확인을 먼저 선호

### B. Decision Record

과거에 사람이 확정한 크리티컬 결정

예:

* 이 서버의 inline in/out은 ens37/ens38
* 이 서비스의 canonical health endpoint는 `/healthz`
* 이 시스템의 로그 주 경로는 `/var/log/suricata/fast.log`

### C. Pattern / Heuristic

반복 관찰된 환경 패턴

예:

* Debian 13 계열에서 `apt + systemd`
* 특정 타겟 태그에서는 collector 포트 5044 사용
* 특정 서비스군은 장애 시 DB pool 문제가 잦음

### D. Outcome

무엇을 했더니 성공/실패했는가

예:

* worker scale-out은 효과 있었음
* cache flush는 일시 완화만 됨
* 특정 WAF 룰은 false positive가 많았음

### E. Policy Shadow

명시 정책은 아니지만 사실상 반복된 운영 규칙

예:

* 운영 DB는 직접 변경 금지, 항상 제안/PR만
* 외부 고객 메일 자동 발송 금지
* 삭제는 승인 없이는 trash까지만

## 저장 방식: RAG vs DB

질문한 부분에 바로 답하면:

### 단기

**DB + 구조화 필드**가 먼저다.

왜냐면 Experience는 검색만 잘 되면 되는 게 아니라,

* 범위
* 신뢰도
* 적용 조건
* 승인 여부
* 마지막 검증 시점
  을 가져야 하기 때문이다.

즉 최소한 이런 구조가 낫다.

```json
{
  "experience_id": "...",
  "type": "decision_record",
  "scope": {
    "user_id": "...",
    "org_id": "...",
    "target_id": "...",
    "target_tags": ["linux", "ids"]
  },
  "key": "inline_iface_pair",
  "value": {"iface_in": "ens37", "iface_out": "ens38"},
  "source": "human_confirmed",
  "confidence": 0.95,
  "created_at": "...",
  "last_validated_at": "...",
  "evidence_refs": [...]
}
```

이건 DB가 맞다.

### 중기

**DB + embedding/RAG 혼합**이 맞다.

정형 필드 검색은 DB로 하고,
비정형 유사도 검색은 vector/RAG로 붙이는 방식이다.

예:

* “이와 비슷한 장애 복구 경험”
* “비슷한 메일 분류 패턴”
* “유사한 환경에서 성공한 설치 흐름”
  같은 건 임베딩 검색이 잘 맞는다.

즉 정답은 둘 중 하나가 아니라:

**정형 Experience DB + 비정형 유사도 검색(RAG) 하이브리드**

이게 맞다.

## Experience는 언제 쓰나

문서의 실행 플로우를 확장하면 이렇게 된다.

1. User request
2. Manager/Master가 goal, unknowns 추출
3. **Experience lookup**
4. Probe/Skill/Plan 생성
5. 실행
6. 결과 저장
7. **Experience update**

기존 Skills 문서의 실행 플로우는 User request → Master가 Skill/Probe/Plan 생성 → 실행 → state/audit/evidence 저장 → 재계획 순서인데, 여기 사이에 Experience lookup/update를 끼우면 된다.

## 중요한 원칙

Experience는 “모델이 알아서 다 하게 만들기 위한 기억”이지만,
아래는 절대 자동으로 넘어가면 안 된다.

* 사용자만 아는 의도
* 승인 필요한 위험 작업
* 시간이 지나면 바뀔 수 있는 중요한 운영 결정
* 한 번 확인됐다고 계속 맞다고 볼 수 없는 환경값

즉 Experience는 **결정을 대체하는 게 아니라, 결정을 보조**해야 한다.

예:

* 이전에 ens37/ens38이었던 경험은 “우선 후보”로만 쓰고
* 실제 적용 전엔 `net.probe`로 다시 확인하거나
* 사용자에게 “여전히 동일한가?”를 물을 수 있어야 한다

## 그래서 OpsClaw 아키텍처를 이렇게 제안한다

### Tool

실행 수단

### Skill

입출력/정책/증빙으로 감싼 재사용 실행 단위

### Experience

과거 human 결정 + 반복 성공 패턴 + 선호 + 검증 결과를 저장/검색하는 기억 계층

### LLM / Master

현재 목표, 현재 상태, Experience, Probe 결과를 종합해서

* 무엇을 확인할지
* 무엇을 실행할지
* 무엇을 물어볼지
  결정

이 구조가 지금 비전과 가장 잘 맞는다.
문서가 말한 LLM Probe Loop, Observation Skills, Tool Lifecycle, 증빙/IR/재현성 철학을 다 살리면서도, 네가 원하는 “사용하면서 점점 더 알아서 하게 만들기”를 설명할 수 있다.

## 다음 개발 방향

내 기준으로 다음은 이렇게 가는 게 맞다.

1. 현재 `input_rationales/evidence_map` 회귀 먼저 수정
2. Observation Domain v0 계속 진행

   * `sys.probe`
   * `svc.probe`
   * `net.probe`
   * `fs.probe`
3. 그 다음 **Experience v0 설계**

   * 스키마
   * 저장 범위
   * lookup 시점
   * update 시점
4. 이후 `answer/clarify` API에서 사용자 확정값을 Experience로 저장

특히 문서에도 Human 최소 질의 엔드포인트(`/projects/{id}/answer` 또는 `/clarify`)가 다음 핵심 TODO로 잡혀 있다. 이건 Experience를 붙이기 딱 좋은 지점이다. 사람의 답을 단순 input으로만 쓰지 말고, 구조화해서 다시 쓰게 해야 한다.

좋아.
그럼 **구현은 뒤로 미루고**, 앞으로 큰 계획에 항상 포함되는 형태로 **OpsClaw의 Tool / Skill / Experience 전체 아키텍처에서 RL/밴딧 적용 포인트 계획**만 정리할게.

핵심 전제는 이거다.

* 현재 OpsClaw의 중심은 여전히 **LLM Probe Loop**, **증거 기반 결정**, **최소 human 질문**, **evidence/audit 저장**이다. RL은 이 본체를 대체하는 게 아니라, **질문/후보/전략 선택을 점점 더 잘하게 만드는 상위 정책 레이어**로 붙어야 한다.
* Skills 문서 기준으로도 구조는 Primitive/Observation/High-Risk/Tool Lifecycle Skill로 나뉘며, RL은 이 Skill을 대신 실행하는 층이 아니라 **어떤 Skill/Probe를 먼저 쓸지 선택 최적화**에 붙는 게 맞다. 

# OpsClaw RL/밴딧 적용 계획

## 1) RL/밴딧의 역할 정의

RL/밴딧은 아래를 담당한다.

* 무엇을 먼저 probe할지
* 언제 자동 확정할지
* 언제 human에게 질문할지
* 어떤 후보를 먼저 제안할지
* 어떤 Experience를 더 신뢰할지
* 어떤 Skill sequence가 현재 목표에 유리할지

즉 **“다음 최선의 선택(next best decision)” 최적화**다.

반대로 RL이 직접 맡으면 안 되는 것은:

* 방화벽 적용
* 데이터 삭제
* 외부 발송
* 계정 잠금
* 정책 위반 가능성이 있는 고위험 실행

이런 건 계속 **정책/승인/롤백 Skill** 아래 있어야 한다. Skills 문서도 `fw.apply_ruleset`, `pkg.install`, `deploy.compose` 같은 고위험 스킬은 승인/정책/롤백을 포함해야 한다고 되어 있다. 

---

## 2) Tool / Skill / Experience / RL 관계

### Tool

실행 수단
예: shell, http, file, browser, OSS CLI

### Skill

통제된 재사용 작업
예: `sys.probe`, `net.probe`, `svc.probe`, `fw.apply_ruleset`, `tool.discover`

### Experience

과거 human 결정, 반복 성공 패턴, 사용자/조직 선호, 검증된 환경 지식 저장

### RL/밴딧

현재 목표 + 현재 상태 + Experience + 최근 evidence를 보고
**무엇을 먼저 물어보고, 무엇을 먼저 확인하고, 어떤 후보를 우선시할지**를 조정

즉 RL은 Tool/Skill/Experience를 사용하는 **정책 레이어**다.

---

## 3) 적용 포인트

## A. Planner/Target/Playbook 후보 정렬

현재 Planner v0는 태그/이름 중심 점수 기반으로 playbook/target을 고른다.
여기에 RL/밴딧을 붙일 수 있다.

### RL/밴딧 역할

* 어떤 target을 우선 후보로 올릴지
* 어떤 playbook을 먼저 제안할지
* ambiguity가 있을 때 어떤 후보 순서로 보여줄지

### 보상 신호

* 사용자 최종 선택과 일치: +
* 추가 질문 없이 실행 성공: ++
* validate 성공: ++
* 잘못 골라 재계획 발생: -

### 구현 우선순위

가장 먼저 붙이기 좋은 포인트 중 하나
이유: 위험이 낮고, 추천 품질 개선 효과가 큼

---

## B. Probe Loop에서 “다음 probe” 선택

문서상 핵심 본체는 여전히 **unknown/missing/ambiguous를 만나면 probe를 생성하고, 결과 기반으로 결정하는 루프**다.

### RL/밴딧 역할

* 어떤 Observation Domain을 먼저 칠지

  * `sys.probe`
  * `svc.probe`
  * `net.probe`
  * `fs.probe`
* probe를 몇 단계까지 더 돌릴지
* 지금 질문할지, probe를 더 할지

### 보상 신호

* 질문 수 감소: +
* probe 횟수 과다: -
* 질문 없이 정확히 해결: ++
* 잘못된 자동결정으로 human 재질문 발생: -

### 구현 우선순위

중요도 높음
특히 “최소 human 질문” 목표와 잘 맞음

---

## C. Human 최소 질문(Human Min Questions) 최적화

문서에서 계속 강조된 게 “정말 필요한 경우만 질문 1~2개로 축소”다.

### RL/밴딧 역할

* 어떤 질문을 먼저 할지
* 질문을 몇 개까지 허용할지
* 질문을 free-form으로 할지 choices로 할지
* 어떤 ambiguity는 사용자에게 넘기고, 어떤 건 자동 결정할지

### 보상 신호

* 질문 수 적음: +
* 질문이 사용자 답변과 직접 연결되어 해결됨: +
* 질문이 모호해서 추가 질문 연쇄 발생: -
* 잘못 자동결정해서 되돌림: 큰 -

### 구현 우선순위

Experience와 붙이면 매우 강력함
예: “이 사용자/조직은 이 류의 결정은 항상 직접 묻는 게 맞다”

---

## D. Experience retrieval / weighting

네가 원한 핵심 포인트다. Experience는 단순 저장보다 **언제 어떤 경험을 꺼내 쓸지**가 더 중요하다.

### RL/밴딧 역할

* 어떤 Experience를 우선 신뢰할지
* 오래된 경험을 얼마나 덜 믿을지
* human-confirmed 경험을 얼마나 우대할지
* target-specific / org-wide / user-specific 경험 중 무엇을 더 볼지

### 보상 신호

* Experience 참고 후 질문 없이 성공: ++
* Experience가 사용자 선택과 일치: +
* Experience 때문에 오판: 큰 -
* 오래된 경험이 validate 실패 유발: -

### 구현 우선순위

중장기 핵심
Experience DB가 먼저 있어야 함

---

## E. Skill sequence 선택

하나의 목표에 대해 어떤 Skill 조합이 효과적인지 최적화할 수 있다.

예:

* 장애 분석 시 `svc.probe → sys.probe → fs.probe`가 나은지
* `net.probe`를 먼저 칠지
* `tool.discover`까지 갈 필요가 있는지

### RL/밴딧 역할

* 다음 Skill 후보 ranking
* 성공률 높은 순서 선택
* 상황별 shortcut 학습

### 보상 신호

* 적은 단계로 해결: +
* validate 통과: ++
* 불필요한 Tool Lifecycle 진입: -
* 실패 후 되돌림: -

### 구현 우선순위

중기
현재는 아직 Observation Domain이 먼저 안정화돼야 함

---

## F. Tool Lifecycle 최적화

장기적으로 중요한 포인트다. 문서에도 M4-2가 Tool Lifecycle Engine으로 잡혀 있다. `Discover → Acquire → Understand → Probe → Execute → Record` 단계가 표준화돼야 한다고 되어 있다. 

### RL/밴딧 역할

* 어떤 OSS 후보를 먼저 시도할지
* README 요약 후 어떤 명령 예제를 먼저 실행할지
* wrapper 생성이 필요한지
* 후보 도구 간 성공률 학습

### 보상 신호

* 목적 달성: ++
* 설치/실행 성공: +
* 도구 도입 후 실패: -
* 더 단순한 기존 Skill로 풀 수 있었는데 과도한 도구 도입: -

### 구현 우선순위

M4 이후

---

## G. 답장/삭제/정책성 작업에서 “질문/자동화 경계” 조정

이메일, 파일 정리, 정책 변경 같은 작업에서 특히 중요하다.

### RL/밴딧 역할

* 이건 자동 draft까지 갈지
* trash까지만 자동으로 할지
* human approval을 요구할지
* 조직/사용자 선호를 얼마나 반영할지

### 보상 신호

* 사용자가 같은 결정을 반복 확인: 자동화 쪽 강화
* 사용자가 자주 뒤집는 결정: 질문 쪽 강화
* 고위험 자동 행동 시도: 큰 패널티

### 구현 우선순위

Experience가 자리 잡은 다음

---

# 4) 보상 함수 초안 원칙

정확한 수치는 나중 문제고, 원칙은 지금부터 로드맵에 포함하면 된다.

### 양의 보상

* 사용자 최종 선택과 예측 일치
* 질문 수 감소
* probe 수 감소
* 실행 성공
* validate 성공
* rollback 없이 종료
* 재현 가능한 evidence/audit 확보

### 음의 보상

* 잘못된 자동결정
* 불필요한 human 질문 증가
* 불필요한 probe 증가
* 실패 후 재시도/재계획 증가
* policy/approval 경계 위반 시도
* rollback 발생
* validate 실패

### 매우 큰 패널티

* 고위험 action을 승인 없이 추진
* 삭제/차단/외부 발송 같은 민감 행동의 오판
* evidence 없이 결정

즉 RL의 목표는 “질문을 없애기”가 아니라
**안전하게, 적은 질문으로, 높은 성공률로, evidence 남기며 해결**이다.

---

# 5) 어떤 RL을 언제 쓸지

처음부터 full RL은 무리다.
순서는 이렇게 가는 게 맞다.

## Stage 0 — Logging only

아직 학습 안 함
아래만 다 저장

* 제안 후보
* 사용자 선택
* probe 수
* 질문 수
* 실행 결과
* validate 결과
* rollback 여부

## Stage 1 — Offline scoring

학습 없이 사후 분석

* 어떤 선택이 잘 맞았는지
* 어떤 Experience가 도움 됐는지
* 어떤 질문이 불필요했는지

## Stage 2 — Rules + weighted ranking

경량 정책

* 최근 성공 경험 가중치 상승
* 실패 경험 감쇠
* human-confirmed 우선

## Stage 3 — Contextual Bandit

가장 추천
왜냐면 현재 상태(context)에서 “다음 한 선택”을 최적화하는 데 적합하다.

* 다음 probe 무엇?
* 질문 vs 자동?
* 후보 순서?
* Experience weighting?

## Stage 4 — RL policy

그 다음
연속 단계 최적화

* multi-step probe policy
* skill sequence policy
* tool lifecycle policy

---

# 6) 로드맵에 넣는 방식

앞으로 큰 계획에는 항상 아래 항목을 포함시키면 된다.

### M3-5.x

* RL/밴딧은 구현 안 함
* 단, **학습용 로그 스키마**는 항상 남김
* human answer / user choice / validate / rollback / approvals 저장 준비

### M4-1 ~ M4-2

* Probe Loop / Observation Domain / Tool Lifecycle 안정화
* RL/밴딧 적용 포인트별 **feature logging 완성**

### M4-3

* Experience DB + retrieval 도입
* offline scoring

### M5

* Contextual Bandit v0

  * planner ranking
  * human_min_questions
  * experience weighting

### M6+

* RL policy v1

  * multi-step probe/skill sequencing
  * tool lifecycle candidate choice
  * personalization / org policy adaptation

---

# 7) 앞으로 문서에 항상 들어가야 할 문장

이 한 줄을 큰 계획서에 고정으로 넣으면 된다.

**“향후 RL/밴딧 레이어를 도입하여, Planner 후보 정렬, Probe 선택, Human 최소 질문, Experience 활용 가중치, Skill sequence를 점진적으로 최적화하되, 고위험 실행 자체는 항상 정책/승인/롤백 Skill 아래 통제한다.”**

이 문장이 지금 비전과 가장 잘 맞는다.
LLM Probe Loop 본체를 유지하면서, 사용자 선택과 실행 결과를 학습 신호로 삼아 점점 더 덜 묻고 더 정확하게 행동하도록 만드는 방향이다.

원하면 다음엔 이걸 바로 **로드맵 문서에 넣을 수 있는 Markdown 섹션 형태**로 정리해주겠다.
