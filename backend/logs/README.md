# Logging System Guide

이 프로젝트는 `app/core/logger.py`를 통해 표준화된 로깅을 수행합니다.

## 1. 로그 저장 위치 (Log Location)

- **Console (Standard Output)**: Docker 컨테이너 로그(`docker logs`)로 수집됩니다. (운영 환경 권장)
- **File**: `backend/logs/app.log` 파일에 텍스트 형태로 저장됩니다. (로컬 디버깅용)

## 2. 사용 방법 (Usage)

```python
from app.core.logger import logger

def my_function():
    logger.info("함수가 실행되었습니다.")
    try:
        # DB 작업 등...
        pass
    except Exception as e:
        logger.error(f"오류 발생: {str(e)}", exc_info=True)
```

## 3. 로그 레벨 (Log Levels)

- `DEBUG`: 개발 중 상세 정보
- `INFO`: 일반적인 작동 상태 확인 (기본값)
- `WARNING`: 예상치 못한 문제지만 실행은 가능한 상태
- `ERROR`: 중대한 오류, 기능 실패
- `CRITICAL`: 시스템 중단 위기

## 4. 로그 포맷 (Format)

```text
2024-02-01 12:34:56 [INFO] [app:45] - Server started successfully
```

- `timestamp`: 발생 시간
- `level`: 로그 레벨
- `name:lineno`: 발생 위치
- `message`: 메시지 내용
