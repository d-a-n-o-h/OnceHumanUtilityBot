
from sqlalchemy import Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Deviants(Base):
    __tablename__ = "deviants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    locations: Mapped[str] = mapped_column(Text, default=None)
    effect: Mapped[str] = mapped_column(Text, default=None)
    happiness: Mapped[str] = mapped_column(Text, default=None)
    sub_type: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(Text, default=None)
