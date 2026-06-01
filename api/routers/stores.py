from fastapi import APIRouter, Request
from api.routers import metrics as metrics_router
from api.routers import funnel as funnel_router
from api.routers import heatmap as heatmap_router

router = APIRouter()


@router.get("/{store_id}/metrics")
async def get_store_metrics(store_id: str, request: Request):
    # Current implementation is store-agnostic; forward request to metrics handler
    return await metrics_router.get_metrics(request)


@router.get("/{store_id}/metrics/summary")
async def get_store_metrics_summary(store_id: str, request: Request):
    return await metrics_router.get_summary(request)


@router.get("/{store_id}/funnel")
async def get_store_funnel(store_id: str, request: Request):
    return await funnel_router.get_funnel(request)


@router.get("/{store_id}/heatmap")
async def get_store_heatmap(store_id: str, request: Request):
    return await heatmap_router.get_heatmap(request)
