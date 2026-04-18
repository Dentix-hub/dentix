"""
================================================================
PATCH B.1 — main.py: حذف @app.on_event("startup") المهجور
================================================================
الملف: backend/main.py
================================================================
"""

# ابحث عن هذا الـ block وأزله بالكامل:
#
# ❌ احذف ده:
# @app.on_event("startup")
# async def startup_event():
#     logger.debug("Application started in debug mode")
#     # ... أي logic تاني هنا

# ✅ وأضف أي logic مفيدة داخل الـ lifespan:
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown logic."""
    # === STARTUP ===
    logger.info("🦷 Dentix API starting up...")
    
    # الـ debug log اللي كان في on_event:
    if app.debug:
        logger.debug("Application started in DEBUG mode")
    
    # أي setup تاني (DB, migrations, seeding, etc.)
    # await create_db_tables()
    # await run_migrations()
    
    logger.info("✅ Dentix API ready")
    
    yield  # ← التطبيق شغال هنا
    
    # === SHUTDOWN ===
    logger.info("🔴 Dentix API shutting down...")
    # await close_db_connections()

# تأكد إن الـ app مُعرَّف بـ lifespan:
app = FastAPI(
    title="Dentix API",
    lifespan=lifespan,
    # ... باقي الـ options
)


"""
================================================================
PATCH B.2 — schemas/inventory.py: Pydantic V2 Migration
================================================================
الملف: backend/schemas/inventory.py
================================================================
ابحث عن كل class Config: وبدّله بـ model_config = ConfigDict(...)
================================================================
"""

# أضف ده في أول الملف (بعد الـ imports الحالية):
from pydantic import BaseModel, ConfigDict

# ================================================================
# النمط العام للتبديل — طبّقه على الـ 8 classes:
# ================================================================

# ❌ قبل (Pydantic V1):
class InventoryItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    tenant_id: int

    class Config:
        from_attributes = True
        populate_by_name = True

# ✅ بعد (Pydantic V2):
class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
    
    id: int
    name: str
    quantity: int
    tenant_id: int

# ================================================================
# SCAN COMMAND — اعرف كم class Config موجود فعلاً:
# grep -n "class Config:" backend/schemas/inventory.py
# ↑ هيظهر أرقام الأسطر — بدّل كل واحدة
# ================================================================

# ================================================================
# ملاحظة: لو فيه أي خاصية تانية في class Config غير المذكورتين،
# زي orm_mode = True (Pydantic V1 قديم):
# ================================================================

# ❌ قديم جداً (Pydantic V1 orm_mode):
class OldSchema(BaseModel):
    class Config:
        orm_mode = True  # ← ده Pydantic V1 فقط

# ✅ Pydantic V2:
class NewSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # ← orm_mode اتغير لـ from_attributes
    )
