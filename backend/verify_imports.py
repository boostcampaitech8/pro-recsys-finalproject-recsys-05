
import sys
import os

# backend 디렉토리를 sys.path에 추가하여 app 모듈을 찾을 수 있게 함
# 실행 위치가 backend라고 가정
sys.path.append(os.getcwd())

try:
    from app.main import app
    print("✅ Import Successful: app.main")
except ImportError as e:
    print(f"❌ Import Failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ An error occurred: {e}")
    sys.exit(1)
