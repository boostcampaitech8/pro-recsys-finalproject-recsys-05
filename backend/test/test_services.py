import os
import redis
from sqlalchemy import create_engine, text

# Localhost connection settings (assuming Docker ports are mapped)
DB_URL = "postgresql://myuser:mypassword@localhost:5432/mydatabase"
REDIS_HOST = "localhost"
REDIS_PORT = 6379

def test_postgres():
    print("\n--- Testing PostgreSQL Connection ---")
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(f"Success! Result: {result.fetchone()}")
    except Exception as e:
        print(f"PostgreSQL Connection Failed: {e}")

def test_redis():
    print("\n--- Testing Redis Connection ---")
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        print("Success! Redis PONG received.")
        r.set("test_key", "hello_redis")
        val = r.get("test_key")
        print(f"Redis Set/Get Test: {val}")
    except Exception as e:
        print(f"Redis Connection Failed: {e}")

if __name__ == "__main__":
    test_postgres()
    test_redis()
