# M1 완료 보고 및 M2 계획 (최신 정리본)

## 1. M1 완료 요약

M1에서는 ChassisClaw의 최소 실행 골격을 확보했다.

완료된 핵심:

- 프로젝트 생성/조회
- `run_auto` 진입
- answer / approve 반영
- validation / retry / replan 최소 루프
- generic `plan_ir` 구조
- skill registry
- 대표 skill `ops.onboard.two_node` 등록
- precheck → probe → decision → report 수준의 stub 실행
- summary artifact 저장

즉 M1은 **문서 설계가 아니라 실행 가능한 골격 확보**로 종료되었다.

---

## 2. M1 한계

- install/action은 stub 수준
- skill 선택은 rule 기반
- target 모델은 아직 테스트용 단순 구조
- 분산/원격 타겟 모델링이 부족
- org profile / experience 미완성

---

## 3. M2 목표

M2의 목표는 아래였다.

> **stub workflow를 운영형 stub workflow로 끌어올리는 것**

즉 단순 보고가 아니라,

- approval 분기
- install plan 생성
- install execution stub
- failure 구조화
- summary 고도화

까지 연결하는 것이 목적이었다.

---

## 4. M2 세부 계획

### M2-1. Approval 이후 실행 분기 연결
- decision 결과를 approval request로 연결
- `/approve` 이후 install 또는 skip 분기 실행

### M2-2. Install job stub
- package manager hint 기반 bootstrap script 초안 생성
- install plan artifact 저장

### M2-3. Probe / Execution contract 일반화
- probe 결과 observation 구조화
- 실패 유형 표준화

### M2-4. Tool/Dependency 부족 대응 설계
- 질문 / 설치 승인 / 대체 도구 / 수동 부트스트랩 중 선택 가능 구조

### M2-5. Skill Runner 확장
- job별 상태
- summary 자동 갱신

### M2-6. Target 모델 강화
- endpoint / transport / auth 정보 모델 정리
- identity 검사 추가

### M2-7. Evidence / Artifact 정리
- summary 중심 artifact에서 확장

### M2-8. 상태기계 정리
- created → planned → resolve → execute → validate → report → completed

---

## 5. 현재 해석

이 문서는 M1 직후 작성된 계획 문서이므로, 새 채팅에서는 아래처럼 보면 된다.

- 이 문서의 M2 계획은 **대부분 이미 수행되었다.**
- 실제 현재 상태는 `02-3.M2_Report_M3_plan_UPDATED.md`를 우선 기준으로 삼는 것이 맞다.
- 다만 M1에서 M2로 넘어갈 때 어떤 문제를 풀려고 했는지 복기하는 용도로는 유효하다.
