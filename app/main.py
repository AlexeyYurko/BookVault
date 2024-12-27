from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.handlers import handlers_router

app = FastAPI(title='BookVault')
app.add_middleware(GZipMiddleware, minimum_size=500)
app.mount('/static', StaticFiles(directory="static"), name="static")
app.include_router(router=handlers_router, prefix="")
