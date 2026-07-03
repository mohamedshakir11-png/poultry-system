from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, ForeignKey, Date, DateTime, Boolean
from datetime import datetime, date

DATABASE_URL = "sqlite+aiosqlite:///./poultry_farm.db"
engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="supervisor", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class BroilerBatch(Base):
    __tablename__ = "broiler_batches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_name: Mapped[str] = mapped_column(String, nullable=False)
    initial_chicks: Mapped[int] = mapped_column(Integer, nullable=False)
    chick_cost_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, default=date.today)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    current_mortality: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class FarmTransaction(Base):
    __tablename__ = "farm_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(Integer, ForeignKey("broiler_batches.id"), nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DailyFeedLog(Base):
    __tablename__ = "daily_feed_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(Integer, ForeignKey("broiler_batches.id"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, default=date.today)
    feed_consumed_kg: Mapped[float] = mapped_column(Float, nullable=False)
    feed_type: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str] = mapped_column(String, nullable=True)

class MedicalSchedule(Base):
    __tablename__ = "medical_schedules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(Integer, ForeignKey("broiler_batches.id"), nullable=False)
    treatment_name: Mapped[str] = mapped_column(String, nullable=False)
    target_age_days: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_administered: Mapped[bool] = mapped_column(Boolean, default=False)
    administered_date: Mapped[date] = mapped_column(Date, nullable=True)
