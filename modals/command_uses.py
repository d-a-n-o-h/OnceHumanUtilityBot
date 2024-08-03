from sqlalchemy import BigInteger, Integer, DateTime, Text, Boolean  # type: ignore
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column  # type: ignore
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class CommandUses(Base):
    __tablename__ = "command_usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    num_uses: Mapped[int] = mapped_column(BigInteger)
    last_used: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(tz=timezone.utc))
    admin: Mapped[bool] = mapped_column(Boolean, default=False)
    