from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import routes_cv, routes_jd, routes_match

app = FastAPI(
    title=settings.app.title,
    version=settings.app.version,
    debug=settings.app.debug
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(routes_cv.router, prefix="/api/v1/cv", tags=["cv"])
app.include_router(routes_jd.router, prefix="/api/v1/jd", tags=["jd"])
app.include_router(routes_match.router, prefix="/api/v1/match", tags=["match"])
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4174",
        "http://127.0.0.1:4174",
        "http://localhost:3000",
        "http://localhost:8000",
        "file://",
        "*"  # Allow all origins for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
