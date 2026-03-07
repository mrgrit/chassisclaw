# OpsClaw 상세 계획서 v1.0

## 0. 문서 목적

본 문서는 OpsClaw의 **제품 목표, 요구사항, 아키텍처, 실행 흐름, 도구/스킬 체계, 상태/에러/안전장치, Master 호출 게이트(PII/기밀검사), 시나리오(운영/보안/유지보수), 보고/감사 체계, MVP 로드맵**을 상세 정의한다.

## 1) 제품 정의

### 1.1 제품 한 줄 정의

**OpsClaw는 폐쇄망에서도 동작 가능한 “업무용 A2A 에이전트 오케스트레이션 플랫폼”**이며, 요구사항을 받아 **계획→스크립트/테스트 생성→원격 실행→검수→보고서**까지 end-to-end로 수행한다.

### 1.2 차별점(범용 에이전트 대비)

- **업무 실행 중심**: 단순 대화/코딩이 아니라 **실제 업무 절차(Todo/Runbook/Test/Rollback)** 수행
- **폐쇄망 우선**: 기본은 **온프레/내부 모델(Ollama)**, 외부 호출은 선택적
- **통제와 감사**: 승인 모드, RBAC, 변경 diff, 작업 이력, 감사 로그
- **상태 기반 워크플로우**: LangGraph로 작업 단계를 노드로 관리, 재시도/분기/중지 조건을 체계화
- **A2A 조직 구조**: Manager ↔ SubAgents, 필요 시 Master로 “검수/조언”만 얻는 구조
- **Master 호출 안전 게이트(필수)**: 개인정보/기밀 포함 여부 검사 + 마스킹/요약/승인

## 2) 사용자/운영 환경 가정

### 2.1 사용 대상

- 운영/인프라/보안/ITSM 담당자
- 폐쇄망/제한망 환경(기관, 제조, 연구소 등)
- 반복되는 구축/운영/점검/문서화 업무 자동화 요구

### 2.2 운영 환경

- SubAgent는 대상 서버(또는 점프호스트)에 설치 가능
- 통신은 내부망 A2A(gRPC/WebSocket) 우선, SSH fallback 지원
- 모델은 기본 내부(로컬) 사용, Master(상용) 호출은 정책에 따라 제한

## 3) 시스템 구성 요소

1. **Frontend**
2. **Manager Agent (LangGraph Orchestrator)**
3. **Sub Agents (대상 시스템별 실행 노드)**
4. **Master Agent (선택적: 외부/상용 고성능 모델)**
5. **RAG Store(문서/플레이북/룰/지식베이스)**
6. **State Store(JSON/DB)**
7. **Audit & Evidence Store(감사 로그/증빙 저장소)**
8. **Policy Engine(Guardrails/PII Gate/RBAC/Stop Conditions)**

## 4) 핵심 기능 요구사항 (FR)

### FR-1. 요구사항 수집/분석

- 자연어 요구사항을 구조화: 목표/범위/제약/리스크/성공 기준
- 모호한 요구사항은 “질문 리스트” 생성(승인 모드에서 질의)

### FR-2. 계획 수립 및 Todo 생성

- 단계별 작업 계획(마일스톤 포함)
- 작업별 “전제조건/위험/롤백/검증” 포함
- Todo는 체크리스트 형태로 Frontend에 표시

### FR-3. 스크립트/테스트 자동 생성

- 각 작업에 대응하는 실행 스크립트(쉘/Ansible-like 템플릿 가능)
- 각 작업에 대응하는 테스트 스크립트(health check/port check/log check)

### FR-4. SubAgent 실행 및 결과 검수

- SubAgent에 스크립트 전달 → 실행 → 출력 수집
- 마일스톤마다 결과 검수(정상/경고/실패) 판단
- 실패 시 원인 후보 축소 + 검증 커맨드로 분기

### FR-5. 상태 저장(State Store)

- OS/NIC/권한/수정파일/설치패키지/실패원인/재시도횟수 등을 JSON 형태로 지속 저장
- 재실행 시 상태를 읽어 “이미 확인한 것” 반복 방지

### FR-6. 안전장치(Guardrails)

- 위험 명령 차단(rm -rf 등)
- 민감 경로 보호(/etc, /var/lib 등은 승인 필요)
- 자동 모드/승인 모드 제공
- 명령/파일/네트워크 접근 범위 정책화

### FR-7. 작업 히스토리/보고서 생성

- 계획서, Todo, 실행 로그, 변경 diff, 테스트 결과, 이슈 분석, 최종 보고서 자동 생성
- 재현 가능한 “증빙 묶음(Evidence Pack)” 생성

### FR-8. Master 호출(선택) 및 검수 흐름

- 해결 불가/고난도 판단 시 Master에 질의
- **질의 전 개인정보/기밀 포함 여부를 반드시 검사(PII/Secret Gate)**

## 5) 비기능 요구사항 (NFR)

- NFR-1: 폐쇄망에서도 Core 기능 동작(내부 모델/로컬 RAG)
- NFR-2: 재현성(동일 상태에서 동일 실행 결과에 수렴)
- NFR-3: 감사 가능성(누가 무엇을 언제 승인/실행했는지)
- NFR-4: 안전성(치명 위험 명령/무분별 외부 전송 방지)
- NFR-5: 확장성(업무 도메인 스킬/플러그인 추가)
- NFR-6: 관측성(메트릭/로그/트레이스)

## 6) LangGraph 기반 워크플로우 설계(Manager)

### 6.1 그래프 노드(예시)

1. **Intake**: 요구사항 수집
2. **Normalize**: 구조화(목표/제약/범위)
3. **Plan**: 마일스톤/리스크/롤백 포함 계획
4. **Todo**: 작업 항목 생성
5. **AssemblePrompt**: 동적 시스템 프롬프트 빌드
6. **GenerateScripts**: 실행 스크립트 생성
7. **GenerateTests**: 테스트 스크립트 생성
8. **Dispatch**: SubAgent에 전달(A2A)
9. **Collect**: 결과/로그 수집
10. **Validate**: 테스트 실행 및 검증
11. **ErrorClassify**: 에러 분류/원인 후보 축소
12. **RetryOrEscalate**: 재시도/수정/중지 판단
13. **MasterGate**: **Master 질의 전 PII/기밀 검사 루틴**
14. **AskMaster**: Master 질의(허용 시)
15. **ApplyFeedback**: 피드백 반영
16. **Report**: 보고서 생성
17. **Close**: 완료/아카이빙

## 7) A2A 통신 설계

### 7.1 메시지 타입

- `HELLO/HEARTBEAT`
- `RUN_SCRIPT`
- `RUN_TEST`
- `UPLOAD_LOGS`
- `UPLOAD_EVIDENCE`
- `STATUS_UPDATE`
- `REQUEST_APPROVAL` (승인 모드)
- `ROLLBACK`
- `CAPABILITIES` (SubAgent 제공 스킬/도구)

### 7.2 표준 결과 포맷(강제)

- exit code
- stdout/stderr
- 주요 파일 변경 목록
- 서비스 상태(systemctl)
- 네트워크 상태(ip a, ip r)
- 증빙(스크린샷 대신 텍스트 증빙: config dump)

## 8) Tools & Skills (모듈화)

### 8.1 공통 스킬

- Workspace Manager (작업 디렉토리/산출물 정리)
- Diff Manager (전/후 비교)
- Backup & Rollback (파일 백업/복원)
- Validator (명령 결과 판정)
- Evidence Pack Builder (증빙 묶음)

### 8.2 시스템/네트워크 스킬

- netplan builder
- DNS/Route/NAT 분석기
- 포트 포워딩 설계기(nftables 중심)
- 서비스/포트 health check

### 8.3 운영 스킬

- journald 분석기
- 리소스 분석(CPU/MEM/Disk)
- 장애 원인 트리아지(runbook)

### 8.4 보안 스킬(초기 도메인)

- Suricata inline 검증/룰 튜닝
- 경량 WAF 설치/정책 튜닝
- SIEM 파이프라인 구성(syslog)
- Sigma 룰 관리/연동
- OpenCTI 피드 연동

> 주의: OpsClaw는 보안에만 한정되지 않으며, 위 스킬은 “초기 적용 업무”의 한 갈래로 관리한다.

## 9) Error Taxonomy (에러 분류기)

### 9.1 분류 체계

- 권한(Permission)
- 네트워크(Network)
- 포트 충돌(Port)
- 의존성(Dependency)
- 설정 문법(Syntax)
- 서비스 기동(Service Start)
- 리소스(Resource)
- 타임아웃(Timeout)

### 9.2 에러 처리 흐름

1. stderr/journalctl 키워드 추출
2. “원인 후보 3개 이내”로 축소
3. 후보별 검증 커맨드 실행
4. 분기 처리(수정/재시도/중지/승인 요청/마스터 요청)

## 10) Stop Conditions (정지 조건)

- 동일 오류 3회 반복
- 네트워크 단절 상태 지속
- 권한 미확보로 진행 불가
- 위험 명령 필요(정책상 자동 불가)
- Master 질의에 필요한 정보가 민감하여 마스킹 불가

→ “무엇이 필요한지” 명확히 제시 후 중지

## 11) Master 호출 안전 게이트(PII/기밀 검사) — 필수 반영

Master는 상용/외부 모델일 수 있으므로, 질의 내용에 **조직 개인정보/기밀정보가 포함될 위험**이 있다.
따라서 OpsClaw는 **MasterGate 루틴을 강제**한다.

### 11.1 MasterGate 정책 목표

- PII/기밀/자격증명/내부 IP/구성/로그 원문이 외부로 나가지 않도록 방지
- 필요한 경우 **마스킹/요약/의미보존 변환** 후 질의
- 정책 위반 시 **차단 + 사용자 승인 또는 로컬 대체**로 전환

### 11.2 탐지 대상(검사 범주)

#### A) 개인정보(PII)

- 성명/전화번호/이메일/주민등록번호 등 식별자
- 사번/직원ID/사용자ID(조직 정책에 따라)
- 사용자 계정 목록/접속 이력(원문)

#### B) 자격증명/비밀정보(Secrets)

- API Key, Token, JWT, Session, Cookie
- SSH Private Key, 인증서 키, DB password
- `.env` 내용, kubeconfig, vault token
- Authorization 헤더, Bearer 토큰

#### C) 기밀정보(Confidential)

- 내부망 IP/호스트명/도메인/라우팅 구조(정책에 따라)
- 시스템 구성 파일 원문(방화벽 룰, SIEM 구성 등)
- 로그 원문(특히 사용자/자격정보/내부자산 식별 포함)

#### D) 보안상 민감한 운영정보(Policy-Sensitive)

- 취약한 설정/우회 가능한 규칙/탐지 회피 힌트
- 침투 테스트 결과의 상세 PoC(정책에 따라)

### 11.3 검사 방식(다층 방어)

1. **정규식/패턴 기반 1차 스캔**
   - 이메일, 전화번호, 주민번호, UUID, JWT, PEM 키 블록
   - AWS/GCP/Azure key 패턴
   - `Authorization: Bearer`
   - `-----BEGIN PRIVATE KEY-----`
   - `.env` 키=값 패턴
2. **사전(Dictionary) 기반 2차 스캔**
   - 조직 도메인/내부 프로젝트 코드명
   - 내부 자산 접두어(hostname 규칙)
   - “confidential”, “internal-use-only” 라벨
3. **LLM 기반 3차 분류(로컬 모델로만)**
   - 내부 모델이 문맥상 민감도 판단
   - “이 텍스트는 외부로 보내도 되는가?” 점수화
   - (중요) 이 단계는 외부 Master가 아니라 **로컬 모델**만 사용
4. **데이터 흐름 정책 엔진 최종 판정**
   - 정책 + 결과 점수로 allow/transform/block 결정

### 11.4 변환(마스킹/요약) 전략

#### 기본 원칙

- “문제 해결에 필요한 최소 정보만” 외부 전송
- 식별 가능한 정보는 “토큰화” 처리
- 설정 원문 대신 “구조 요약” 전송

#### 예시 변환 규칙

- 내부 IP: `10.1.0.80` → `INTERNAL_IP_1`
- 호스트명: `siem01.corp.local` → `HOST_A`
- 사용자명: `jdoe` → `USER_1`
- 토큰/키: `abcd...` → `[REDACTED_TOKEN]`
- 로그 원문: 주요 에러 라인만 추출 + 식별정보 제거

#### 의미보존 요약 템플릿

- 환경: OS, 버전, 서비스 이름(일반화)
- 증상: 오류 메시지(민감부분 제거)
- 시도: 이미 수행한 조치 요약
- 질문: 원하는 해답의 형태(조언/설계/디버깅 포인트)

### 11.5 MasterGate 의사결정 플로우

1. Manager가 Master 호출 필요 판단
2. **MasterGate 실행**: scan → classify → policy decision
3. 결정
   - **ALLOW**: 그대로 질의
   - **TRANSFORM**: 마스킹/요약 후 질의
   - **BLOCK**: 외부 전송 금지
4. BLOCK인 경우 대체
   - 로컬 모델 재시도
   - 로컬 RAG 검색 강화
   - 사용자 승인 요청(정책상 허용 시)
   - 민감정보 제거 후 게이트 재시도

### 11.6 Frontend 반영(사용자 투명성)

- Master 호출 시 **전송될 프롬프트 미리보기(마스킹 후)** 표시
- 마스킹 항목 **Diff/리스트 제공**
- 승인 모드일 경우 **사용자 승인 버튼** 필요
- 감사 로그 기록 항목
  - 누가 승인했는지
  - 어떤 정책으로 마스킹되었는지
  - 원문은 로컬에만 저장(암호화)

### 11.7 저장/보관 정책

- 원문(민감 포함)은 **로컬 Evidence Store에 암호화 저장**
- 외부 전송본(마스킹/요약)은 별도 저장
- 정책 위반 시도는 경고 이벤트로 기록

## 12) 초기 구축 시나리오(요구사항 반영)

### 12.1 구성 요약

1. **방화벽**: 192.168.208.132(ens33) / 10.1.0.1(ens34)
   - nftables 설치됨(운영 편의에 맞게 조정 가능)
2. **IPS**: 192.168.208.138(ens38 외부 작업용) + ens33(방화벽 연결) + ens34(WAF 연결)
   - Suricata 설치됨, inline, ens33/34 IP 없음
3. **WAF/Web**: 192.168.208.140(ens37 외부 작업용) + ens33(내부 10.1.0.80)
   - netplan으로 ens33=10.1.0.80
   - 경량 WAF 설치 + WebGoat 배포
   - syslog/auditd/osquery 설치(엔드포인트 보호)
4. **SIEM**: 192.168.208.137(관리용) + 내부 NIC 10.1.0.200
   - SIEM 설치(운영자가 관리하기 좋은 것으로)
   - OpenCTI + Sigma 설치 및 연동
   - syslog 기반 로그 수집 + IPS/WAF agent 허용

### 12.2 구축 마일스톤 및 검증(샘플)

- **M1. 네트워크 확정**
  - netplan 적용
  - 라우팅/게이트웨이 검증
  - `ping`, `curl`, `ss -lntp`
- **M2. 방화벽 포트포워딩**
  - 80/tcp 외부 → WAF/Web(10.1.0.80) 포워딩
  - NAT 룰/필터 룰 분리
  - 테스트: 외부에서 80 접속 성공
- **M3. IPS inline 검증**
  - inline bridge/AF_PACKET 모드 확인
  - drop 테스트(테스트 룰로 샘플 트래픽 차단)
  - 성능 측정(pps/CPU)
- **M4. WAF + WebGoat 배포**
  - 경량 WAF 선정(예: Nginx + ModSecurity 최소 코어룰셋)
  - WebGoat 서비스 구동
  - 테스트: 정상 페이지/로그/차단 로그
- **M5. 로그 수집 파이프라인**
  - syslog 송신/수신 규칙
  - SIEM 인입 확인
  - 테스트: 각 장비에서 test log 전송
- **M6. 엔드포인트 기본 보호**
  - auditd, osquery, syslog 설정
  - 규칙/수집 항목 최소 세팅
  - 테스트: 이벤트 생성 후 SIEM 확인
- **M7. SIEM + OpenCTI + Sigma 연동**
  - Sigma 룰 파이프라인 구축
  - OpenCTI 인텔 피드 연결(폐쇄망은 오프라인 import 포함)
  - 테스트: 샘플 IOC 매칭 이벤트 확인

## 13) 운영 업무 시나리오(상세)

### O-1: WAF 정상 트래픽 차단(False Positive)

1. WAF/리버스프록시 로그 수집
2. 차단 룰 ID 식별
3. 룰 영향 분석(범위/빈도/대상 URI)
4. 우회(예외) vs 룰 조정 결정(승인 모드)
5. 변경 적용
6. 회귀 테스트(정상/공격 트래픽)
7. 보고서(변경 diff, 영향도, 테스트 결과)

### O-2: IPS CPU 급증/드롭 증가

1. pps, drop, queue 확인
2. 룰셋/프로토콜 분포 분석
3. 과다 룰 후보 추출
4. 룰 그룹 분리/비활성화(테스트)
5. 성능 재측정
6. 튜닝 결과 문서화

### O-3: SIEM 로그 누락

1. 송신 측 syslog 상태 확인
2. 방화벽/라우팅/포트 확인
3. 수신 측 파이프라인 확인
4. test message 재전송
5. 정상화/원인 기록

### O-4: Web 서비스 장애 (502/504/타임아웃)

1. upstream 상태 확인
2. WAF 설정 변경 이력 확인
3. 포트 충돌/리소스 이슈 확인
4. 롤백 또는 핫픽스
5. 재발 방지 체크리스트 추가

## 14) 보안 업무 시나리오(상세)

### S-1: WebGoat 기반 SQLi 공격 탐지/상관분석

1. 공격 트래픽 생성(테스트 케이스)
2. WAF 탐지 로그 확인
3. IPS 탐지 로그 확인
4. SIEM correlation 룰 적용
5. Sigma 룰 생성/적용
6. OpenCTI에 TTP/IOC 매핑(가능 시)

### S-2: 관리자 계정 브루트포스 대응

1. 로그인 실패 이벤트 수집
2. 임계치 초과 시 자동 차단(방화벽/WAF)
3. 정책 강화(계정 잠금/레이트리밋)
4. 보고서 + 재현 테스트

### S-3: 설정 파일 무단 변경 탐지(auditd/osquery)

1. `/etc` 주요 파일 감시 룰 구성
2. 변경 발생 시 SIEM 알림
3. 변경 diff 생성
4. 승인 기록과 대조(미승인 변경 시 이슈 생성)

## 15) 유지보수/정기점검 시나리오(상세)

### M-1: 월간 패치 & 리부트 계획

- 영향 분석 → 샌드박스 적용 → 테스트 → 운영 반영
- 롤백 포인트 확보(설정 백업, 서비스 설정 스냅샷)

### M-2: 룰/정책 업데이트

- IPS 룰 업데이트
- WAF CRS 업데이트(또는 경량 룰셋)
- 회귀 테스트(정상/공격)

### M-3: 로그/인덱스/스토리지 점검

- 디스크 사용량
- 보존 정책
- SIEM 인덱스 최적화

### M-4: 백업/복구 리허설

- 설정 파일/룰셋/키 구성요소 백업
- 복구 스크립트 테스트
- 복구 시간(RTO) 기록

## 16) Frontend 상세 설계

### 16.1 Dashboard

- 대상 시스템(방화벽/IPS/WAF/SIEM) 상태
- 각 시스템 health/서비스 상태
- 최근 이슈/경고/차단 이벤트 카운트
- 로그 수집 상태(수집률, 지연)

### 16.2 설정

- 에이전트 등록/연결 테스트
- 모델 설정(로컬/외부)
- Guardrails 정책
- **MasterGate 정책(PII/기밀 검사 수준, 마스킹 규칙)**
- 승인 모드/자동 모드

### 16.3 작업(프로젝트)

- 진행중: Todo, 승인대기, 마일스톤, 실시간 로그
- 완료: 보고서/증빙 다운로드, 변경 diff

## 17) 데이터/저장소 설계(필수 추가)

### 17.1 저장소 종류

- State Store: 작업 상태(JSON + DB)
- Artifact Store: 스크립트/테스트/리포트/템플릿
- Evidence Store: 로그/설정덤프/결과(암호화)
- Audit Log: 사용자 승인/정책/전송 기록

### 17.2 감사 로그 필수 항목

- 사용자/역할
- 승인 여부
- 수행 명령 요약
- 변경 파일 목록
- MasterGate 결과(allow/transform/block)
- 전송된 프롬프트 해시(원문 비보관 가능)

## 18) MVP 범위(권장)

### MVP-1 (1차)

- Manager + SubAgent 1~2종
- A2A 실행/결과 수집
- Todo/스크립트/테스트/보고서
- Guardrails + Stop Conditions
- **MasterGate(PII/기밀 검사 + 마스킹 + 승인)**

### MVP-2 (2차)

- 플레이북/템플릿 플러그인
- RAG 통합 강화
- diff/rollback 고도화
- RBAC/조직 사용자 관리

### MVP-3 (3차)

- 업무 도메인 확장(ITSM/문서/자산/클라우드 등)
- 정책 엔진 고도화(조직별 규정)
- 폐쇄망 오프라인 업데이트/패키징 완성

## 19) 구현 시 반드시 들어가야 하는 추가 항목(누락 방지)

1. **Secrets Vault(로컬 암호화 저장)**
2. **MasterGate(PII/기밀 검사) + 프롬프트 미리보기/승인 UI**
3. **Evidence Pack(증빙 자동 저장)**
4. **RBAC(관리자/운영자/승인자)**
5. **Diff/Rollback(자동 백업 포함)**
6. **Offline Packaging(폐쇄망 배포 번들)**
7. **정책 엔진(명령/경로/네트워크 접근 통제)**

## 20) OpsClaw 결론(정체성)

OpsClaw는 “오픈 범용 에이전트”가 아니라 **업무용 자율 오케스트레이션 시스템**이며, 특히 **폐쇄망에서도 동작**한다.

외부 Master 호출이 필요한 순간에도,

> **MasterGate(PII/기밀 검사 루틴)로 조직 데이터 유출 가능성을 원천적으로 통제한다.**
