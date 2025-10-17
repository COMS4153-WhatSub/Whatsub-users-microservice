import os
import sys
if __package__ is None or __package__ == "":
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.utils.settings import get_settings
from app.utils.logger import init_logger
from app.middleware.request_logger import RequestLoggingMiddleware
from app.middleware.error_handler import register_error_handlers
from app.services.user_service import InMemoryUserService, SqlAlchemyUserService
from app.utils.db import get_session_factory, create_all, get_engine
from app.resources.health import router as health_router
from app.resources.users import router as users_router


settings = get_settings()
logger = init_logger(settings)

openapi_tags = [
    {
        "name": "health",
        "description": "Service health and readiness checks.",
    },
    {
        "name": "users",
        "description": "Operations for managing user accounts.",
    },
]

app = FastAPI(
    title=settings.app_name,
    description="Whatsub Users Microservice",
    version="0.1.0",
    contact={
        "name": "Whatsub Team",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware, logger=logger)

register_error_handlers(app, logger)

# Choose service based on database configuration
if all([settings.db_host, settings.db_user, settings.db_pass, settings.db_name]):
    try:
        engine = get_engine()
        create_all(engine)  # Create tables if they don't exist
        session_factory = get_session_factory()
        app.state.user_service = SqlAlchemyUserService(logger, session_factory)
        logger.info("database_connected", host=settings.db_host, database=settings.db_name)
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        logger.info("falling_back_to_in_memory")
        app.state.user_service = InMemoryUserService(logger)
else:
    logger.info("no_database_configuration_using_in_memory")
    app.state.user_service = InMemoryUserService(logger)

app.include_router(health_router, prefix="")
app.include_router(users_router, prefix="/users", tags=["users"])


@app.get("/")
async def root():
    return {"service": settings.app_name, "status": "running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
