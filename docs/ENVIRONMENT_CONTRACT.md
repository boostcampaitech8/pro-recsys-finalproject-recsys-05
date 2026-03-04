# 운영 환경변수 계약서 (`.env.prod`)

## 목적

배포/운영 안정성을 위해 운영 환경변수 계약을 명확히 정의합니다.

- 단일 진실원(SSoT): 서버에서 직접 관리하는 `.env.prod`
- 범위: 단일 서버 Docker Compose 운영 배포
- 목표: `docker compose pull/up` 이전에 필수 키 누락을 즉시 실패 처리

## 단일 진실원 규칙

1. 운영 런타임 환경파일은 서버의 `.env.prod`만 수동 관리합니다.
2. CI/CD는 운영 시크릿 값을 덮어쓰지 않습니다.
3. Compose 호환을 위해 `.env`가 필요하면, 배포 시 `.env.prod`에서 파생 생성하며 수동 수정하지 않습니다.

## 필수 키

아래 키는 반드시 존재해야 하며, 빈 값이면 안 됩니다.

| 키 | 사용처 | 담당 | 비고 |
| --- | --- | --- | --- |
| `DATABASE_URL` | 백엔드 DB 연결 | Backend | `postgresql+asyncpg://...` |
| `REDIS_URL` | 백엔드 캐시/세션 | Backend | `redis://...` |
| `DOCKER_USERNAME` | Compose 이미지 경로 해석 | Infra/DevOps | Docker Hub 네임스페이스 |
| `IMAGE_TAG` | 배포 대상 이미지 태그 | Infra/DevOps | 운영은 릴리즈 태그 정책 준수 |
| `STEAM_API_KEY` | Steam 연동 | Backend | 외부 API 자격증명 |
| `CLOVA_API_KEY` | 챗/리랭커 연동 | Backend/AI | 외부 API 자격증명 |
| `CLOVA_BASE_URL` | 챗 엔드포인트 | Backend/AI | 챗 완성 API 기본 URL |
| `CLOVA_RERANKER_URL` | 리랭커 엔드포인트 | Backend/AI | 리랭커 API URL |

## 선택 키

기능 요구가 없다면 생략 가능하며, 필요 시에만 채웁니다.

| 키 | 기본값/동작 |
| --- | --- |
| `ENV` | 앱 런타임 모드 (운영은 `prod` 권장) |
| `DEBUG_MODE` | 운영 기본 `False` |
| `BENTOML_SERVICE_URL` | 기본 `http://bentoml:3000` |
| `ML_REC_ROOT` | 미설정 시 컨테이너 기본 경로 사용 |
| `BENTOML_SKIP_GCS_BOOTSTRAP` | 현재 compose 기본값 `false` |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCS 인증키 파일 경로 |
| `GCS_KEY_BASE64` | 서버 파일키를 별도 관리하지 않을 때 선택적으로 사용 |

## 변경 절차

1. 서비스 담당자(`Backend` 또는 `Infra/DevOps`) 승인 후 변경합니다.
2. 권한 있는 운영자가 서버 `.env.prod`를 직접 수정합니다.
3. `bash scripts/validate_env.sh .env.prod`를 실행합니다.
4. 검증 통과 후에만 `./deploy.sh`를 실행합니다.
5. 변경 이력(누가/언제/무엇)을 운영 로그 또는 티켓에 기록합니다.

## 시크릿 로테이션 절차

1. 제공자 콘솔에서 신규 시크릿 발급
2. `.env.prod`에 신규 값 반영
3. `scripts/validate_env.sh` 검증
4. 배포 및 헬스체크 확인
5. 정상 반영 확인 후 구 시크릿 폐기

## 롤백 절차

1. 이전 `.env.prod` 스냅샷(또는 보안 백업본) 복원
2. `scripts/validate_env.sh .env.prod` 재검증
3. `./deploy.sh` 재실행으로 이전 값 재적용
4. 헬스 엔드포인트 및 핵심 API 스모크 테스트 확인

## 배포 전 체크리스트

- [ ] 서버에 `.env.prod` 파일이 존재한다
- [ ] 모든 필수 키가 비어 있지 않다
- [ ] API 키 변경/로테이션 이력이 기록되어 있다
- [ ] `scripts/validate_env.sh .env.prod`가 통과했다
- [ ] 운영 배포 대상 이미지 태그를 확인했다
