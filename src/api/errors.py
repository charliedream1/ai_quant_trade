"""FastAPI exception handlers."""

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.exceptions import BusinessError, ErrorCode
from src.core.logger import get_logger
from src.core.redaction import redact, redact_text

logger = get_logger("api.errors")


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "-"))


async def business_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, BusinessError):
        logger.warning(
            "business error handled | request_id={} method={} path={} code={} message={}",
            _request_id(request),
            request.method,
            request.url.path,
            exc.code,
            redact_text(exc.message),
        )
        return JSONResponse(
            status_code=200,
            content={
                "code": exc.code,
                "message": redact_text(exc.message),
                "data": redact(exc.data),
                "request_id": _request_id(request),
            },
        )
    return await unhandled_error_handler(request, exc)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, RequestValidationError):
        logger.warning(
            "validation error handled | request_id={} method={} path={} errors={}",
            _request_id(request),
            request.method,
            request.url.path,
            len(exc.errors()),
        )
        return JSONResponse(
            status_code=200,
            content={
                "code": int(ErrorCode.INVALID_PARAM),
                "message": "参数格式或取值非法",
                "data": redact(
                    jsonable_encoder(
                        [{key: error[key] for key in ("loc", "msg", "type") if key in error} for error in exc.errors()]
                    )
                ),
                "request_id": _request_id(request),
            },
        )
    return await unhandled_error_handler(request, exc)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled backend error | request_id={} method={} path={} error_type={} detail={}",
        _request_id(request),
        request.method,
        request.url.path,
        type(exc).__name__,
        redact_text(str(exc)),
    )
    return JSONResponse(
        status_code=200,
        content={
            "code": int(ErrorCode.UNKNOWN),
            "message": "未知内部错误",
            "data": None,
            "request_id": _request_id(request),
        },
    )
