import logging
import sys
from pathlib import Path

# 로그 저장 디렉토리 (없으면 생성)
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def setup_logging(level=logging.INFO):
    """
    애플리케이션 전체 로깅 설정을 초기화합니다.
    - Console (Stdout): Docker/Kubernetes 환경 표준
    - File (Optional): logs/app.log (로컬 디버깅용)
    """
    
    # 기본 포맷: [시간] [레벨] [모듈명:줄번호] - 메시지
    log_format = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Root Logger 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 기존 핸들러 초기화 (중복 방지)
    if root_logger.handlers:
        root_logger.handlers = []

    # 2. Console Handler (Stdout) - Docker 환경 필수
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)


    # 3. Third-party 라이브러리 로그 레벨 조정 (너무 시끄러운 로그 방지)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    
    # 로거 인스턴스 반환
    logger = logging.getLogger("app")
    logger.info("Logging setup complete.")
    return logger

# 싱글톤처럼 사용할 수 있게 미리 로거 생성
logger = setup_logging()
