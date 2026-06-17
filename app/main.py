from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.handlers import handlers_router
from app.logging_config import setup_logging

setup_logging()

app = FastAPI(title='BookVault')
app.add_middleware(GZipMiddleware, minimum_size=500)
app.mount('/static', StaticFiles(directory=settings.static_path), name="static")
app.include_router(router=handlers_router, prefix="")
