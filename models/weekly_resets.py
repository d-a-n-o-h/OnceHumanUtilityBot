from sqlalchemy import BigInteger, Boolean, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Purification(Base):
    __tablename__ = "purification_reset_day"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    role_id: Mapped[int] = mapped_column(BigInteger, default=None)
    reset_day: Mapped[int] = mapped_column(Integer)
    auto_delete: Mapped[bool] = mapped_column(Boolean, default=False)

class Controller(Base):
    __tablename__ = "controller_reset_day"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    role_id: Mapped[int] = mapped_column(BigInteger, default=None)
    reset_day: Mapped[int] = mapped_column(Integer)
    auto_delete: Mapped[bool] = mapped_column(Boolean, default=False)

class Sproutlet(Base):
    __tablename__ = "sproutlet"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    role_id: Mapped[int] = mapped_column(BigInteger, default=None)
    hour: Mapped[int] = mapped_column(Integer)
    auto_delete: Mapped[bool] = mapped_column(Boolean, default=False)