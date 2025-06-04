from sqlalchemy import BigInteger, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class Lunar(Base):
    __tablename__ = "event_timers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event: Mapped[str] = mapped_column(Text, default='lunar')
    last_alert: Mapped[int] = mapped_column(BigInteger)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    role_id: Mapped[int] = mapped_column(BigInteger, default=None)
    added_by: Mapped[int] = mapped_column(BigInteger)
    auto_delete: Mapped[bool] = mapped_column(Boolean, default=False)