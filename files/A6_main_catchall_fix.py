"""
================================================================
PATCH A.6 — main.py SPA Catch-All Fix
================================================================
الملف: backend/main.py
================================================================
"""

from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse

# ================================================================
# ابحث عن الـ catch-all route الحالي وبدّله بالكامل بالكود ده:
# ================================================================

# ❌ قبل (النمط الشائع الغلط):
# @app.get("/{full_path:path}")
# async def serve_spa(full_path: str):
#     return FileResponse("static/index.html")
#
# المشكلة: بيرجع index.html حتى لـ /api/ routes اللي مش موجودة
# وبيسبب confusion للـ frontend بدل 404 واضح

# ✅ بعد — الـ catch-all الصح:
EXCLUDED_PREFIXES = (
    "api/",
    "api",           # exact match
    "static/",
    "assets/",
    "uploads/",
    "auth/",
    "docs",          # FastAPI swagger
    "redoc",         # FastAPI redoc
    "openapi.json",  # FastAPI schema
)

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """
    SPA catch-all: يخدم index.html لكل الـ frontend routes.
    يستثني الـ API routes وأي static assets.
    """
    # استثني الـ backend routes
    if full_path == "" or full_path.startswith(EXCLUDED_PREFIXES):
        raise HTTPException(
            status_code=404,
            detail=f"API endpoint '/{full_path}' not found"
        )

    # تحقق إن ملف index.html موجود فعلاً
    index_path = Path("static/index.html")
    if not index_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Frontend build not found. Run 'npm run build' first."
        )

    return FileResponse(
        index_path,
        headers={
            # منع caching للـ HTML (عشان الـ app updates تشتغل فوراً)
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


# ================================================================
# ملاحظة مهمة — الترتيب في main.py:
# ================================================================
# تأكد إن الـ catch-all route جاي في آخر الملف بعد كل الـ routers:
#
# app.include_router(auth_router, prefix="/api/v1")
# app.include_router(users_router, prefix="/api/v1")
# app.include_router(appointments_router, prefix="/api/v1")
# ... باقي الـ routers
#
# @app.get("/{full_path:path}")  ← الـ catch-all في الآخر
# async def serve_spa(...):
#     ...
# ================================================================
