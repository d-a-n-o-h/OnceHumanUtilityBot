from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class GuildLanguage(Base):
    __tablename__ = "guild_lang"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    added_by: Mapped[int] = mapped_column(BigInteger)
    lang: Mapped[str] = mapped_column(String)