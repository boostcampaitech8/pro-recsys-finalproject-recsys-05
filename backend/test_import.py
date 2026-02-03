import sys
import os

print(f"CWD: {os.getcwd()}")
print("SYS.PATH:")
for p in sys.path:
    print(f"  - {p}")

try:
    import app
    print(f"App package: {app}")
    print(f"App path: {app.__file__}")

    import app.domains.game
    print(f"Game package: {app.domains.game}")
    
    import app.domains.game.schemas
    print(f"Game schemas module: {app.domains.game.schemas}")
    print(f"Game schemas file: {app.domains.game.schemas.__file__}")

    from app.domains.game.schemas import GameInfo
    print(f"Successfully imported GameInfo: {GameInfo}")

except ImportError as e:
    print(f"ImportError: {e}")
except AttributeError as e:
    print(f"AttributeError: {e}")
except Exception as e:
    print(f"Error: {e}")
