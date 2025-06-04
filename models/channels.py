from sqlalchemy import BigInteger, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class PremiumMessage(Base):
    __tablename__ = "premium_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    alert_type: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)


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
    asian_server: Mapped[bool] = mapped_column(Boolean)

class CrateMutes(Base):
    __tablename__ = "crate_mutes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('craterespawn_channels.guild_id'))
    zero: Mapped[bool] = mapped_column(Boolean)
    four: Mapped[bool] = mapped_column(Boolean)
    eight: Mapped[bool] = mapped_column(Boolean)
    twelve: Mapped[bool] = mapped_column(Boolean)
    sixteen: Mapped[bool] = mapped_column(Boolean)
    twenty: Mapped[bool] = mapped_column(Boolean)

class CargoMutes(Base):
    __tablename__ = "cargo_mutes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('cargoscramble_channels.guild_id'))
    twelve: Mapped[bool] = mapped_column(Boolean)
    fifteen: Mapped[bool] = mapped_column(Boolean)
    twenty_two: Mapped[bool] = mapped_column(Boolean)
    eighteen_thirty: Mapped[bool] = mapped_column(Boolean)

class AutoDelete(Base):
    __tablename__ = "auto_delete"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    crate: Mapped[bool] = mapped_column(Boolean, default=False)
    cargo: Mapped[bool] = mapped_column(Boolean, default=False)

class Medics(Base):
    __tablename__ = "medics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    auto_delete: Mapped[bool] = mapped_column(Boolean)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    role_id: Mapped[int] = mapped_column(BigInteger, default=None)
    added_by: Mapped[int] = mapped_column(BigInteger)