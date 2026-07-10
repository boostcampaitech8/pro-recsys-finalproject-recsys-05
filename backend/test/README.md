# Backend Testing Guide

이 디렉토리는 백엔드 서비스의 단위·통합 테스트 코드를 포함합니다.
정본 규칙은 `docs/SPEC.md` §6(테스트 규칙)입니다.

## 1. 마커 체계 (T16 · SPEC §6)

모든 테스트는 세 마커 중 하나로 분류됩니다 (`pyproject.toml [tool.pytest.ini_options]`에 등록, `--strict-markers`).

| 마커 | 의미 | 외부 의존 |
|---|---|---|
| `unit` | 외부 의존 0 — DB·Redis·네트워크 없이 실행 (기본 러너) | 없음 (스텁·fake httpx·monkeypatch) |
| `integration` | 실제 DB·Redis 필요 | docker compose 선행 |
| `manual` | 실제 외부 API 호출 — 기본 skip, env 가드로만 실행 | 실 API 키 |

파일 상단에 `pytestmark = pytest.mark.<marker>`로 부착합니다.

## 2. 실행 방법

```bash
cd backend

# 단위 테스트 — DB/Redis 없이 실행 (가장 빠름, CI 기본 게이트)
uv run pytest -m unit

# 통합 테스트 — compose 선행 필요
docker compose up -d db redis
uv run pytest -m integration

# 전체(단위+통합)
uv run pytest -m "unit or integration"
```

> `manual` 테스트는 `-m manual` + 해당 env 가드(`RUN_CLOVA_TEST=1`, `RUN_MANUAL_USER_FLOW=1`)를
> 함께 지정해야 실행됩니다. 기본 러너에서는 선택되지 않습니다.

## 3. 격리 (conftest.py)

- DB fixture(`db`)는 **autouse가 아닙니다** — `integration` 테스트가 명시적으로 요청할 때만
  실제 커넥션이 열립니다. 따라서 `-m unit`은 DB 설정 없이 실행됩니다.
- `db`는 **트랜잭션 롤백**으로 테스트 간 격리합니다: 스키마는 커밋해 영속화하고,
  테스트가 만든 데이터(앱 코드의 `commit()` 포함)는 세이브포인트에 갇혀 종료 시 롤백됩니다.
- `.env`가 없는 개발 머신에서도 단위 테스트가 import되도록, conftest가 실제 `.env`를
  우선 존중하고 없을 때만 더미 `DATABASE_URL`로 폴백합니다(더미로는 연결하지 않음).

## 4. CI/CD

- `.github/workflows/deploy.yml`이 `pgvector/pgvector:pg15`·`redis:alpine` 서비스 컨테이너로
  격리 환경을 구성해 PR·Push 시 자동 실행합니다.
