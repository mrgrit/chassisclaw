# ChassisClaw 사용 케이스 (최신판)

이 문서는 새 채팅에서 ChassisClaw의 지향점과 구현 우선순위를 설명할 때 참고하는 **대표 사용 케이스 문서**다.  
기존 사용 케이스의 강점은 유지하되, 현재 구조 변경을 반영하여 아래 관점을 추가로 명확히 한다.

- 실행 대상 선택은 `target` 단독 개념이 아니라 **asset 탐색 → target resolve** 구조다.
- 원격 시스템은 먼저 **asset으로 온보딩**되고, 이후 작업 시 target으로 해석된다.
- Tool Lifecycle과 evidence-first 원칙은 모든 케이스의 기본 전제다.

---

# 사용 케이스 1) 원인 모르는 서비스 지연/장애 자동 복구

## 사용자 목표
- “웹이 갑자기 느려졌어. 원인 찾아서 복구해. 재발 방지까지.”

## 흐름
### Plan
- 서비스 경로(웹→API→DB→캐시) 가설 구성
- 관련 asset 탐색
- 실행 가능한 target resolve

### Probe
- CPU/Load/Mem/Swap
- Disk/IO
- 포트/프로세스
- 최근 로그
- 필요 시 DB / GC / 커넥션 풀 추가 probe

### Decide
- 원인 후보 ranking
- 즉시 완화와 근본 수정 분리

### Exec
- 재시작, worker 증설, 임시 rate limit 등
- 정책상 위험 작업은 승인 후 실행

### Validate
- p95 / error rate / health check 재확인

### Replan
- 개선 없으면 다음 원인 후보로 확장

## 산출물
- audit 타임라인
- evidence pack
- 최종 복구 보고서

---

# 사용 케이스 2) 신규 서버 5대 온보딩

## 사용자 목표
- “신규 서버 5대 기본 셋업(계정/SSH/보안/모니터링/로그) 해줘.”

## 흐름
### Plan
- 주소 또는 선택 기준으로 asset 후보 식별
- 아직 등록되지 않은 시스템은 bootstrap 단계로 전환

### Bootstrap / Asset Registration
- subagent 설치 또는 연결
- `/health`, `/capabilities` 확인
- asset registry 등록

### Exec
- 계정/키/권한
- 패키지 업데이트
- 모니터링/로그 에이전트 설치
- 보안 기본 설정

### Validate
- 서비스 상태
- heartbeat
- 포트/접속 검증

## 산출물
- asset 등록 결과
- 서버별 결과 요약
- evidence ZIP

---

# 사용 케이스 3) 전체 보안 점검 + 보고서 자동 생성

## 사용자 목표
- “전체 서버 취약 설정/열린 포트/취약 패키지 점검해서 보고서 만들어.”

## 흐름
### Plan
- asset 그룹 선택
- 필요한 스캐너가 없으면 Tool Lifecycle 수행

### Probe
- 열린 포트
- ssh 설정
- sudoers
- 패키지 목록

### Tool Lifecycle
- OSS 검색
- clone / install
- README / help 학습
- wrapper 생성으로 JSON 정규화

### Validate
- 재스캔으로 개선 확인

## 산출물
- 점검 보고서
- evidence ZIP

---

# 사용 케이스 4) 네트워크 구조 파악 및 인터페이스 판별

## 사용자 목표
- “이 서버에서 인라인 in/out 인터페이스를 정확히 판별해.”

## 흐름
### Plan
- 관련 asset 선택
- unknown: iface_in / iface_out / route / gateway

### Probe
- `ip -j link show`
- `ip -j addr`
- `ip -j route`
- 필요 시 짧은 패킷 관찰

### Decide
- 증거 기반 판정
- 애매하면 질문 1개로 축소

### Validate
- 선택된 인터페이스 기반 경로 검증

## 산출물
- 결론
- 근거 명령 세트
- evidence

---

# 사용 케이스 5) IDS/로그 파이프라인 장애 추적

## 사용자 목표
- “Suricata 로그가 SIEM으로 안 올라가. 어디서 끊겼는지 찾고 복구해.”

## 흐름
- 관련 asset 탐색: sensor / forwarder / collector / SIEM 접점
- 각 asset에 대한 target resolve
- health / queue / port / 로그 probe
- 장애 구간 pinpoint
- 설정/서비스 재시작 또는 권한 수정
- end-to-end 흐름 재검증

## 산출물
- 장애 구간 보고
- 복구 증빙

---

# 사용 케이스 6) 방화벽 정책 변경

## 사용자 목표
- “API 서버는 443만 열고 나머지는 차단. 변경 후 접속 테스트까지.”

## 흐름
- asset 선택
- 현재 규칙 및 영향 범위 probe
- 변경안 생성
- approval gate
- 적용 후 smoke test
- 실패 시 자동 롤백

## 산출물
- 변경 diff
- 검증 결과
- 롤백 증빙

---

# 사용 케이스 7) 필요한 도구가 없을 때 OSS 도입

## 사용자 목표
- “PCAP에서 특정 패턴 트래픽만 추출해 통계 내줘. 도구 없으면 알아서 찾아 써.”

## 흐름
- 필요한 기능 정의
- Tool Lifecycle 수행
- OSS 도구 확보 및 실험 실행
- wrapper 생성
- 실제 데이터 처리
- 결과 저장

## 산출물
- 사용한 OSS 버전/커밋
- 실행 명령
- 결과 JSON
- 보고서

---

# 사용 케이스 8) DB 백업/복구 리허설

## 사용자 목표
- “백업 잘 되는지 확인하고, 복구 리허설까지 수행해서 증빙 남겨.”

## 흐름
- 관련 asset 탐색
- 백업 존재/최근성/크기 확인
- 격리 환경 target resolve
- 복구 실행
- 쿼리 / 무결성 검증

## 산출물
- 백업/복구 로그
- 검증 결과
- evidence

---

# 사용 케이스 9) IAM/권한 감사

## 사용자 목표
- “권한 과다 계정 찾고 정리안 만들고, 승인 후 적용.”

## 흐름
- asset별 사용자/그룹/권한 수집
- 위험 권한 패턴 분류
- 조정안 생성
- 승인 후 적용
- 업무 영향 검증

## 산출물
- 변경 전/후 diff
- 승인 기록
- evidence

---

# 사용 케이스 10) 성능 튜닝

## 사용자 목표
- “API p95가 튀어. 원인 찾고 개선해. 개선 전/후 증빙 남겨.”

## 흐름
- 관련 asset 탐색
- 지표/로그/리소스 동시 수집
- 병목 후보별 실험 계획
- 필요 시 벤치/프로파일러 OSS 도입
- 설정 변경 후 비교 검증

## 산출물
- 전/후 비교 리포트
- 성능 근거 evidence

---

# 사용 케이스 11) 보안 이벤트 대응

## 사용자 목표
- “이상 트래픽. 감염 조사하고 필요한 조치 실행. 증빙 남겨.”

## 흐름
- IOC 기반 asset 탐색
- 프로세스/연결/로그/무결성 probe
- 격리/차단 필요 여부 판정
- 조사 자동화
- 위험 조치는 승인 후 실행
- 재발 여부 검증

## 산출물
- 탐지→조사→조치→검증 타임라인
- 증거 파일 묶음

---

# 사용 케이스 12) 주간 운영 리포트 자동 생성

## 사용자 목표
- “이번 주 장애/변경/조치/승인 내역을 증빙과 함께 보고서로.”

## 흐름
- project / audit / evidence index 수집
- 중요 이벤트 정리
- 요약/리스크/개선사항 도출
- 보고서 생성

## 산출물
- 운영 리포트
- 관련 evidence ZIP

---

# 현재 개발 우선순위와 연결되는 사용 케이스

지금 코드 상태와 가장 직접 연결되는 건 아래 두 개다.

1. **신규 서버 2대 온보딩**
2. **자산 등록 후 실행 대상 resolve**

즉 새 채팅에서는 대표 사용 케이스를 아래처럼 잡고 시작하면 된다.

> 원격 VM 2대를 subagent와 함께 asset으로 등록하고, `ops.onboard.two_node` skill이 이 두 asset을 받아 실행 target으로 resolve한 뒤, precheck → probe → decision → install/report 흐름을 수행하도록 만든다.
