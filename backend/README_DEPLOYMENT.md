## 데이터베이스 관리 (운영)

서버의 데이터베이스는 `postgres_data` 볼륨에 영구 저장됩니다. 로컬 테스트 DB의 데이터는 서버로 자동 배포되지 **않습니다**. (스키마만 코드를 통해 생성됨)

### 데이터 초기화 방법

이미 서버에 데이터가 쌓여있고, 이를 정리하고 싶을 때 사용합니다.

#### 방법 1: 테이블 데이터만 삭제 (SQL)

컨테이너 내부로 들어가서 특정 테이블을 비우거나 삭제합니다.

```bash
# 1. DB 컨테이너 접속
docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB

# 2. 데이터 삭제 (TRUNCATE가 DELETE보다 빠름)
TRUNCATE TABLE games;

# 3. 테이블 삭제 (스키마 변경 필요 시)
DROP TABLE games;
```

#### 방법 2: 완전 초기화 (Volume Reset)

볼륨 자체를 날려버리는 가장 강력한 방법입니다. (주의: 모든 데이터가 삭제됨)

```bash
# 1. 서버 중지 및 볼륨 삭제 (-v 옵션 필수)
docker compose -f docker-compose.prod.yml down -v

# 2. 서버 다시 시작 (깨끗한 상태로 DB 새로 생성됨)
docker compose -f docker-compose.prod.yml up -d
```
