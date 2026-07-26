from fastapi import FastAPI
from app.database import test_database_connection
from app.routers import tickets, dashboard, auth

app = FastAPI(
    title="Campus ServiceDesk API",
    description="Backend API for Campus ServiceDesk and Asset Management System",
    version="1.0.0"
)

app.include_router(tickets.router)
app.include_router(dashboard.router)
app.include_router(auth.router)


@app.get("/")
def root():
    return {"message": "Campus ServiceDesk API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db-health")
def database_health_check():
    database_name = test_database_connection()
    return {
        "status": "connected",
        "database": database_name
    }