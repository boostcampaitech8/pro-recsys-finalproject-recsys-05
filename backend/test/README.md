# Backend Testing Guide

이 디렉토리는 백엔드 서비스의 기능 및 통합 테스트 코드를 포함합니다.

## 1. 테스트 환경 (Test Environment)

테스트는 `pgvector` 확장이 설치된 PostgreSQL과 Redis가 필요합니다.

### CI/CD 환경 (GitHub Actions)

- `deploy.yml`에 정의된 `pgvector/pgvector:pg15` 및 `redis:alpine` 서비스 컨테이너를 자동으로 사용하여 격리된 환경에서 테스트합니다.
- 별도의 설정 없이 PR이나 Push 시 자동으로 실행됩니다.

### 로컬 개발 환경 (Local)

로컬에서 테스트를 실행하려면 Docker Compose로 DB와 Redis를 먼저 실행해야 합니다.

```bash
# 1. 개발용 DB 및 Redis 실행
docker compose up -d db redis

# 2. 테스트 실행 (backend 디렉토리에서)
# 주의: 'ModuleNotFoundError: No module named app' 에러 방지를 위해 python -m 모드로 실행해야 합니다.
cd backend
uv run python -m pytest test/
```

### 특정 테스트 파일 실행 예시

```bash
uv run python -m pytest test/domains/game/test_game_flow.py
```

## 2. 테스트 파일 구조

- `test_services.py`: DB(PostgreSQL) 및 Redis 연결 테스트.
- `test_gcs.py`: Google Cloud Storage 연동 테스트. (실제 요청을 보내므로 GCS 키 필요)

## 3. 주의 사항

- `test_gcs.py`는 실제 클라우드 리소스를 사용할 수 있으므로, 로컬 테스트 시 `.env`에 `GCS_KEY_BASE64`가 올바르게 설정되어 있는지 확인하세요.
- CI 환경에서는 `GCS_KEY_BASE64`가 Secrets로 주입되지 않는 한 GCS 테스트는 실패할 수 있으니 `pytest.mark.skip` 처리가 필요할 수 있습니다.
