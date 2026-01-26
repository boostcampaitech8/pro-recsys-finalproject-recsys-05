from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter()

@router.get("/")
def health_check():
    return {"status": "ok"}

@router.get("/db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/gcs")
def health_check_gcs():
    try:
        from app.storage import get_gcs_client
        client = get_gcs_client()
        if not client:
             return {"status": "error", "message": "GCS client initialization failed"}
        buckets = list(client.list_buckets(max_results=1))
        return {"status": "ok", "message": "GCS connection successful", "bucket_count_check": len(buckets)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
