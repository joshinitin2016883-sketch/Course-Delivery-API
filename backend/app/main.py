"""The FastAPI application: routers, CORS and error handling. Run from backend/:
python -m uvicorn app.main:app --reload
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import CORS_ORIGINS
from app.routers import activity, auth, courses, enrollments, instructors, lessons
from app.services.errors import Conflict, InvalidInput, NotAuthenticated, NotFound, PermissionDenied, ServiceError

app = FastAPI(title="Course Delivery API")

# Let the frontend (a different origin) call the API. Logins use a header, not cookies, so no credentials mode.
# A browser only lets the page read a few response headers from another origin; Content-Disposition carries
# the CSV export's filename, so it is exposed too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# The one place where service errors become HTTP status codes.
STATUS_CODES = {
    NotAuthenticated: 401,
    PermissionDenied: 403,
    NotFound: 404,
    Conflict: 409,
    InvalidInput: 422,
}


@app.exception_handler(ServiceError)
async def handle_service_error(request: Request, error: ServiceError) -> JSONResponse:
    status_code = STATUS_CODES.get(type(error), 400)
    # A 401 must say which sign-in scheme the API expects.
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(status_code=status_code, content={"detail": str(error)}, headers=headers)


@app.get("/health")
def health() -> dict[str, str]:
    """For Render's health check: answers without touching the database."""
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(lessons.router)
app.include_router(activity.router)
app.include_router(enrollments.router)
app.include_router(instructors.router)
