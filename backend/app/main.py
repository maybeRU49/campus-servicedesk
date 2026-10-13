import logging
import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.database import test_database_connection
from app.routers import assets, auth, dashboard, lookups, technicians, tickets
from app.security import require_roles


app = FastAPI(
    title="Campus ServiceDesk API",
    description="Backend API for Campus ServiceDesk and Asset Management System",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(dashboard.router)
app.include_router(technicians.router)
app.include_router(lookups.router)
app.include_router(assets.router)


@app.get("/")
def root():
    return {
        "message": "Campus ServiceDesk API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    # Avoid logging SQL parameters, which may contain credentials or private text.
    logging.getLogger(__name__).error("Database operation failed: %s", type(exc).__name__)
    return JSONResponse(status_code=503, content={
        "detail": "Database operation failed. Please try again later."
    })


@app.get("/db-health", dependencies=[Depends(require_roles("ADMIN"))])
def database_health_check():
    database_name = test_database_connection()

    return {
        "status": "connected",
        "database": database_name
    }
