
import os
import time
import uuid

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware


ALLOWED_ORIGIN = "https://dash-0im51o.example.com"

# Set EMAIL to your exact logged-in email address before deployment.
EMAIL = os.environ.get("EMAIL", "REPLACE_WITH_YOUR_EMAIL")


api = FastAPI()

# Only the assigned website is allowed.
api.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)


@api.get("/stats")
def get_stats(values: str = Query(...)):
    # Convert "10,20,30" into [10, 20, 30].
    try:
        numbers = [int(item.strip()) for item in values.split(",")]
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="values must contain comma-separated integers",
        )

    if not numbers:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No values provided")

    return {
        "email": EMAIL,
        "count": len(numbers),
        "sum": sum(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "mean": sum(numbers) / len(numbers),
    }


class RequestMetricsMiddleware:
    """Add request ID and processing time to every response."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                elapsed = max(0.0, time.perf_counter() - start_time)

                headers = list(message.get("headers", []))
                headers.extend([
                    (b"x-request-id", request_id.encode("ascii")),
                    (b"x-process-time", f"{elapsed:.6f}".encode("ascii")),
                ])

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_headers)


# Wrap the whole FastAPI/CORS application so even preflight
# responses receive the required middleware headers.
app = RequestMetricsMiddleware(api)