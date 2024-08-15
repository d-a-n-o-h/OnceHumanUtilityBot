from sqlalchemy import BigInteger, Integer # type: ignore
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column # type: ignore

class Base(DeclarativeBase):
    pass

class CrateRespawnChannel(Base):
    __tablename__ = "craterespawn_channels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    role_id: Mapped[int] = mapped_column(BigInteger, default=None)
    added_by: Mapped[int] = mapped_column(BigInteger)

class CargoScrambleChannel(Base):
    __tablename__ = "cargoscramble_channels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    role_id: Mapped[int] = mapped_column(BigInteger, default=None)
    added_by: Mapped[int] = mapped_column(BigInteger)