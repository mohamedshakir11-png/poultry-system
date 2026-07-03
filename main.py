from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from datetime import datetime, date, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, sum as sql_sum

from database import engine, Base, get_db, User, BroilerBatch, FarmTransaction, DailyFeedLog, MedicalSchedule

app = FastAPI(title="نظام إدارة مزارع التسمين اللاحم المتكامل", version="2026.1")

# --- الأمان والتشفير (JWT Auth) ---
SECRET_KEY = "SUPER_SECRET_KEY_FOR_POULTRY_SYSTEM_2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_password_hash(password): return pwd_context.hash(password)
def verify_password(plain, hashed): return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    exc = HTTPException(status_code=401, detail="تعذر التحقق من الهوية، سجل الدخول مجدداً")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise exc
    except JWTError: raise exc
    res = await db.execute(select(User).where(User.username == username))
    user = res.scalar_one_or_none()
    if user is None or not user.is_active: raise exc
    return user

class RoleChecker:
    def __init__(self, allowed_roles: list[str]): self.allowed_roles = allowed_roles
    def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(status_code=403, detail="عذراً، لا تمتلك الصلاحية الكافية للوصول")
        return current_user

allow_all = RoleChecker(["owner", "supervisor"])
allow_owner_only = RoleChecker(["owner"])

# --- نماذج التحقق (Schemas) ---
class UserRegister(BaseModel): username: str; password: str; role: str
class BatchCreate(BaseModel): batch_name: str; initial_chicks: int; chick_cost_per_unit: float; start_date: Optional[date] = None
class TransactionCreate(BaseModel): category: str; amount: float; quantity: Optional[float] = None; notes: Optional[str] = None
class FeedLogCreate(BaseModel): feed_consumed_kg: float; feed_type: str; notes: Optional[str] = None
class MedicalCreate(BaseModel): treatment_name: str; target_age_days: int; scheduled_date: date

# --- إعداد الجداول تلقائياً عند الإقلاع ---
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# --- نقاط الاتصال (Endpoints) ---

@app.post("/api/auth/register", tags=["الأمان والصلاحيات"])
async def register(p: UserRegister, db: AsyncSession = Depends(get_db)):
    hp = get_password_hash(p.password)
    db_user = User(username=p.username, hashed_password=hp, role=p.role)
    db.add(db_user)
    await db.commit()
    return {"message": "تم تسجيل المستخدم بنجاح"}

@app.post("/api/auth/login", tags=["الأمان والصلاحيات"])
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.username == form.username))
    user = res.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    t = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": t, "token_type": "bearer", "role": user.role}

@app.post("/api/batches", tags=["إدارة الدورات الإنتاجية"])
async def create_batch(p: BatchCreate, db: AsyncSession = Depends(get_db), u: User = Depends(allow_owner_only)):
    b = BroilerBatch(**p.model_dump())
    db.add(b)
    await db.commit()
    return {"message": "تم فتح الدورة الإنتاجية بنجاح", "batch_id": b.id}

@app.post("/api/operations/{batch_id}/feed", tags=["العمليات اليومية (مشرف / مالك)"])
async def log_feed(batch_id: int, p: FeedLogCreate, db: AsyncSession = Depends(get_db), u: User = Depends(allow_all)):
    log = DailyFeedLog(**p.model_dump(), batch_id=batch_id)
    db.add(log)
    await db.commit()
    return {"message": "تم تسجيل استهلاك العلف اليومي"}

@app.post("/api/operations/{batch_id}/mortality", tags=["العمليات اليومية (مشرف / مالك)"])
async def log_mortality(batch_id: int, count: int, db: AsyncSession = Depends(get_db), u: User = Depends(allow_all)):
    b = await db.get(BroilerBatch, batch_id)
    if not b: raise HTTPException(status_code=404, detail="الدورة غير موجودة")
    b.current_mortality += count
    await db.commit()
    return {"message": "تم تحديث عدد النفوق اليومي بنجاح", "current_total_mortality": b.current_mortality}

@app.post("/api/financials/{batch_id}/transaction", tags=["الإدارة المالية (المالك فقط)"])
async def add_transaction(batch_id: int, p: TransactionCreate, db: AsyncSession = Depends(get_db), u: User = Depends(allow_owner_only)):
    t = FarmTransaction(**p.model_dump(), batch_id=batch_id)
    db.add(t)
    await db.commit()
    return {"message": "تم تسجيل المعاملة المالية بنجاح"}

@app.get("/api/dashboard/{batch_id}/analytics", tags=["لوحة التحكم والتحليلات (المالك فقط)"])
async def get_analytics(batch_id: int, db: AsyncSession = Depends(get_db), u: User = Depends(allow_owner_only)):
    b = await db.get(BroilerBatch, batch_id)
    if not b: raise HTTPException(status_code=404, detail="الدورة غير موجودة")
    
    # حساب المصاريف والإيرادات
    t_res = await db.execute(select(FarmTransaction).where(FarmTransaction.batch_id == batch_id))
    txs = t_res.scalars().all()
    
    chick_cost = b.initial_chicks * b.chick_cost_per_unit
    feed_cost = sum(t.amount for t in txs if t.category == "feed")
    med_cost = sum(t.amount for t in txs if t.category == "medicine")
    util_cost = sum(t.amount for t in txs if t.category == "utility")
    revenue = sum(t.amount for t in txs if t.category == "revenue")
    
    total_expenses = chick_cost + feed_cost + med_cost + util_cost
    net_profit = revenue - total_expenses
    
    # حساب كفاءة العلف المتراكمة
    f_res = await db.execute(select(DailyFeedLog).where(DailyFeedLog.batch_id == batch_id))
    feeds = f_res.scalars().all()
    total_feed_consumed_kg = sum(f.feed_consumed_kg for f in feeds)
    
    # حساب نسبة الهلاك الحيوية
    mortality_rate = (b.current_mortality / b.initial_chicks) * 100 if b.initial_chicks > 0 else 0
    
    return {
        "batch_name": b.batch_name,
        "initial_chicks": b.initial_chicks,
        "current_mortality_count": b.current_mortality,
        "mortality_rate": f"{mortality_rate:.2f}%",
        "financials": {
            "chick_purchase_cost": chick_cost,
            "feed_expenses": feed_cost,
            "medicine_expenses": med_cost,
            "utilities_expenses": util_cost,
            "total_expenses": total_expenses,
            "total_revenue": revenue,
            "net_profit": net_profit
        },
        "operations": {
            "total_feed_consumed_kg": total_feed_consumed_kg
        }
    }
