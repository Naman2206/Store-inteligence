from fastapi import APIRouter, Request
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    loader = request.app.state.loader
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "rows_loaded": len(loader.df),
        "store": "Brigade_Bangalore",
        "date": "2026-04-10",
    }
