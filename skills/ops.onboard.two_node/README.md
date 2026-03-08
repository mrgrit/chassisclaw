# ops.onboard.two_node

두 개의 타겟 노드를 ChassisClaw 관리 범위에 편입하기 위한 초기 온보딩 스킬.

## 목적
- 두 노드가 등록되어 있는지 확인
- 각 노드의 기본 상태와 capabilities를 수집
- subagent 설치 필요 여부를 판단
- 설치 승인/차단 사유를 남김
- 최종 온보딩 요약을 생성

## 현재 범위
이 버전은 실행 로직 완성본이 아니라 스킬 골격이다.
즉, LLM/Planner가 선택할 수 있는 대표 스킬의 구조를 먼저 고정하는 단계다.

## 예상 흐름
1. target 존재 확인
2. node A probe
3. node B probe
4. 필요 시 subagent 설치 여부 판단
5. 보고서 생성

## 이후 확장 예정
- 실제 subagent 배포 액션
- package manager 자동 판별
- SSH/bootstrap wrapper 생성
- health 검증 재시도
- evidence pack 생성