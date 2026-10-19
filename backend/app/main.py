import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title="Intelligent Invoice Processing & Payment Automation", version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins.split(","),
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Automation-Key"],
)
app.include_router(router)


@app.get("/", include_in_schema=False)
def api_home():
    return RedirectResponse(url="/docs")


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Invalid request",
                "fields": [
                    {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                    for e in exc.errors()
                ],
            }
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    code = 409 if isinstance(exc, IntegrityError) else 503
    logging.getLogger(__name__).error(
        "Database operation failed: %s", type(exc).__name__
    )
    return JSONResponse(
        status_code=code,
        content={
            "error": {
                "code": code,
                "message": "Concurrent update conflict; retry or refresh"
                if code == 409
                else "Database temporarily unavailable",
            }
        },
    )
