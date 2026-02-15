import uuid
import logging
from fastapi import Request


async def correlation_middleware(request: Request, call_next):
    correlation_id = str(uuid.uuid4())

    request.state.correlation_id = correlation_id

    response = await call_next(request)

    response.headers["X-Correlation-ID"] = correlation_id

    return response
