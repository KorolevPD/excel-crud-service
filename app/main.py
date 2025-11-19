from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import router as table_reports_router

app = FastAPI(
    title="Excel CRUD Service",
    description="API для работы с Excel-файлами",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(table_reports_router, prefix="/api/v1", tags=["Table Reports"])
