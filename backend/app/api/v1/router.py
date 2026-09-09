from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.scenes import router as scenes_router
from app.api.v1.detection import router as detection_router
from app.api.v1.slicks import router as slicks_router
from app.api.v1.environment import router as environment_router
from app.api.v1.drift import router as drift_router
from app.api.v1.ais import router as ais_router
from app.api.v1.vessels import router as vessels_router
from app.api.v1.attribution import router as attribution_router
from app.api.v1.investigations import router as investigations_router
from app.api.v1.reports import router as reports_router
from app.api.v1.demo import router as demo_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(scenes_router)
api_v1_router.include_router(detection_router)
api_v1_router.include_router(slicks_router)
api_v1_router.include_router(environment_router)
api_v1_router.include_router(drift_router)
api_v1_router.include_router(ais_router)
api_v1_router.include_router(vessels_router)
api_v1_router.include_router(attribution_router)
api_v1_router.include_router(investigations_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(demo_router)
