# 새 채팅 시작용 부트스트랩 문서

## 1. 현재 상태 한 줄 요약

ChassisClaw는 **M1 완료, M2 완료, M3 진행 중**이며, 지금 가장 중요한 작업은 **target 중심 잔재를 걷어내고 asset 중심 구조로 전환하는 것**이다.

---

## 2. 새 채팅에서 반드시 먼저 공유할 것

1. 현재 레포 zip 또는 최신 코드
2. 아래 최신화된 문서들
   - `00-1_CSClaw_plan_구체화_UPDATED.md`
   - `01_M1_plan_UPDATED.md`
   - `02-3.M2_Report_M3_plan_UPDATED.md`
   - `02-4.M3설계변경_구성_상세정의서_UPDATED.md`
   - `02-5.M3설계변경_Asset추가_UPDATED.md`
   - `USER_CASE_UPDATED.md`

---

## 3. 새 채팅에서 먼저 말해야 할 핵심 전제

- ChassisClaw는 Tool-driven execution loop system이다.
- 관리 기준은 target이 아니라 asset이다.
- remote VM 2대를 진짜 asset으로 쓰는 방향으로 간다.
- local-agent-1/local-agent-2는 테스트 잔재일 뿐 장기 기준이 아니다.
- onboarding의 산출물은 target 등록이 아니라 asset 등록/갱신이다.
- 실행 시점에 asset을 target으로 resolve한다.

---

## 4. 현재 가장 시급한 개발 작업

### 1순위
- `core/app/models/asset.py`
- `core/app/storage/asset_store.py`
- `data/state/assets/*.json`

### 2순위
- `core/app/api/assets.py`
- FastAPI router 등록

### 3순위
- `ops.onboard.two_node`를 asset 기준으로 리팩토링
  - `check_targets_exist` → `check_assets_exist`
  - `_probe_target` → `_probe_asset_subagent`
  - summary를 asset 기준으로 수정

### 4순위
- remote VM 2대 실제 subagent 온보딩 테스트

---

## 5. 새 채팅에서 첫 명령 추천

```bash
grep -R "def execute_stub" -n core
grep -R "_build_onboarding_summary" -n core
grep -R "_probe_target" -n core
```

그리고 바로 다음 파일부터 작업:

```text
core/app/models/asset.py
core/app/storage/asset_store.py
```

---

## 6. 현재 판단 기준

### 이미 끝난 것
- M1
- M2

### 아직 안 끝난 것
- M3 asset 전환
- remote asset 기준 onboarding
- target을 파생 실행 객체로 축소

---

## 7. 새 채팅 첫 요청 예시

> 현재 레포 코드를 기준으로 asset 중심 M3 리팩토링을 시작하자.  
> 우선 `core/app/models/asset.py`, `core/app/storage/asset_store.py`, `core/app/api/assets.py`를 만들고, `ops.onboard.two_node`의 target 기반 흐름을 asset 기반으로 바꿔줘.  
> remote VM 2대(192.168.208.143, 192.168.208.144)를 기준 자산으로 본다.
