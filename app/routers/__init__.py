from fastapi import APIRouter
from . import (
    admin,
    certificates,
    core,
    node,
    subscription,
    subscription_routing,
    system,
    user_template,
    user,
    home,
)

api_router = APIRouter()

routers = [
    admin.router,
    certificates.router,
    core.router,
    node.router,
    subscription.router,
    subscription_routing.router,
    system.router,
    user_template.router,
    user.router,
    home.router,
]

for router in routers:
    api_router.include_router(router)

__all__ = ["api_router"]