import os
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import create_engine, String, Integer, ForeignKey, Text, DateTime, Boolean, Float, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.engine import Engine
from config import MAIN_DB

# --- Backward-compatible path constants ---
DB_FOLDER = str(MAIN_DB.parent)
DB_NAME = MAIN_DB.name
DB_PATH = str(MAIN_DB)

# --- SQLAlchemy Setup ---
class Base(DeclarativeBase):
    pass

# --- Models ---

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    aliases: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Comma separated
    yahoo_ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True) # Override for data fetching
    name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="To Research") # To Research, In Progress, Done
    
    # Relationships
    documents: Mapped[List["Document"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    time_logs: Mapped[List["TimeLog"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    calendar_events: Mapped[List["CalendarEvent"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Company(ticker='{self.ticker}', name='{self.name}')>"

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(1024), unique=True) # Absolute or relative path in Vault
    doc_type: Mapped[str] = mapped_column(String(50)) # e.g., 'EarningsCall', '10K', '10Q'
    year: Mapped[int] = mapped_column(Integer)
    quarter: Mapped[Optional[str]] = mapped_column(String(10), nullable=True) # Q1, Q2, Q3, Q4, FY
    
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    company: Mapped["Company"] = relationship(back_populates="documents")

class TimeLog(Base):
    __tablename__ = "time_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    company: Mapped["Company"] = relationship(back_populates="time_logs")

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    
    event_date: Mapped[datetime] = mapped_column(DateTime) # Store as datetime (midnight) or date
    event_type: Mapped[str] = mapped_column(String(50)) # Earnings, Presentation, Dividend
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual, yfinance, etc
    status: Mapped[str] = mapped_column(String(20), default="Scheduled") # Scheduled, Completed, Missed
    
    is_automated: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    est_eps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    company: Mapped["Company"] = relationship(back_populates="calendar_events")

# --- Special Situations Models ---

class SpecialSituation(Base):
    __tablename__ = "special_situations"

    id: Mapped[str] = mapped_column(String(50), primary_key=True) # UUID or slug
    title: Mapped[str] = mapped_column(String(255))
    tickers: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # JSON list
    
    event_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    strategy_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    entry_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    deal_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # target_price equivalent
    capital_allocated: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    target_date: Mapped[Optional[date]] = mapped_column(DateTime, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(DateTime, nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), default="Pipeline")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    
    probability: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 to 1.0
    
    specific_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON
    sensitivity_data: Mapped[str] = mapped_column(Text, default="{}") # JSON - REQUIRED BY DB
    common_data: Mapped[str] = mapped_column(Text, default="{}") # JSON - REQUIRED BY DB
    checklist_data: Mapped[str] = mapped_column(Text, default="{}") # JSON - REQUIRED BY DB
    doc_links: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON
    
    folder_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Thesis / Risks
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    time_logs: Mapped[List["SpecialTimeLog"]] = relationship(back_populates="situation", cascade="all, delete-orphan")

class SpecialTimeLog(Base):
    __tablename__ = "special_time_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    situation_id: Mapped[str] = mapped_column(ForeignKey("special_situations.id"))
    
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    situation: Mapped["SpecialSituation"] = relationship(back_populates="time_logs")

# --- Wealth & Analytics Models (F7) ---

class Account(Base):
    """A financial account (Bank, IBKR, Fundsmith, Mortgage, Real Estate)"""
    __tablename__ = "wealth_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100)) # e.g. "Cuenta Bank of scot. Master"
    type: Mapped[str] = mapped_column(String(50)) # bank, brokerage, fund, mortgage, real_estate, loan
    # internal_debt = special loan type where one owner owes another (doesn't affect total net worth)
    
    owner: Mapped[str] = mapped_column(String(20)) # "Rafa", "Cris", "Comun"
    currency: Mapped[str] = mapped_column(String(3), default="EUR") # EUR, GBP, USD
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    balances: Mapped[List["AccountBalance"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="account", cascade="all, delete-orphan")

class MonthlySnapshot(Base):
    """The closing of each month, saving exchange rates and dates."""
    __tablename__ = "wealth_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    month_id: Mapped[str] = mapped_column(String(7), unique=True, index=True) # "YYYY-MM" e.g., "2025-12"
    closing_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Official Exchange Rates for the month's snapshot
    gbp_to_eur: Mapped[float] = mapped_column(Float, default=1.18) 
    usd_to_eur: Mapped[float] = mapped_column(Float, default=0.92)
    
    comun_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    balances: Mapped[List["AccountBalance"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")

class AccountBalance(Base):
    """The balance of a specific account at a specific month's close."""
    __tablename__ = "wealth_balances"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("wealth_accounts.id"))
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("wealth_snapshots.id"))
    
    # E.g. what you put in
    invested_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0) 
    # E.g. what it's worth now (For banks, invested_amount == current_value)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Relationships
    account: Mapped["Account"] = relationship(back_populates="balances")
    snapshot: Mapped["MonthlySnapshot"] = relationship(back_populates="balances")

class TransactionCategory(Base):
    """User-defined categories for expenses/income"""
    __tablename__ = "wealth_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    type: Mapped[str] = mapped_column(String(20)) # "Expense", "Income", "Transfer"
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True) # Hex color

class Transaction(Base):
    """Individual bank/brokerage statements lines (Gastos X)"""
    __tablename__ = "wealth_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("wealth_accounts.id"))
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("wealth_categories.id"), nullable=True)
    
    date: Mapped[date] = mapped_column(DateTime)
    amount: Mapped[float] = mapped_column(Float) # Negative for expenses, Positive for income
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    
    description: Mapped[str] = mapped_column(String(255))
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False) # True if user accepted category
    
    # Relationships
    account: Mapped["Account"] = relationship(back_populates="transactions")
    # Using string mapping for category to avoid order issues
    category: Mapped[Optional["TransactionCategory"]] = relationship()

class IncomeRecord(Base):
    """Monthly salary/income tracker (Ingresos X)"""
    __tablename__ = "wealth_income"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(20)) # Rafa, Cris
    month_id: Mapped[str] = mapped_column(String(7), index=True) # "2025-12"
    
    gross_amount: Mapped[float] = mapped_column(Float, default=0.0)
    net_amount: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    
    
    total_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    shared_quota: Mapped[float] = mapped_column(Float, default=0.0)
    
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    
    hours_worked: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    holidays: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tips: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # --- Database Initialization ---

def init_db(db_path: str = DB_PATH):
    """Initializes the database and creates tables.
    Uses config.MAIN_DB by default. Accepts optional override for testing.
    """
    # Ensure the db/ folder exists
    path = db_path if db_path != DB_PATH else str(MAIN_DB)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    
    engine = create_engine(f"sqlite:///{path}", echo=False, connect_args={'check_same_thread': False})
    
    # Enable Foreign Keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine

def get_session_factory(engine: Engine):
    return sessionmaker(bind=engine)

if __name__ == "__main__":
    print(f"Initializing database at {DB_PATH}...")
    engine = init_db()
    print("Database initialized successfully.")
