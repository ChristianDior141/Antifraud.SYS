from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, clients, documents, transactions, aml, reviews, analytics, admin,
    incidents, detection_rules, privacy,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(clients.router)
api_router.include_router(documents.router)
api_router.include_router(transactions.router)
api_router.include_router(aml.router)
api_router.include_router(reviews.router)
api_router.include_router(analytics.router)
api_router.include_router(admin.router)
api_router.include_router(incidents.router)
api_router.include_router(detection_rules.router)
api_router.include_router(privacy.router)
