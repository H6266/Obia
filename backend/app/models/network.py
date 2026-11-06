from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Network(Base):
    __tablename__ = "networks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    short_name: Mapped[str] = mapped_column(String(32), nullable=False)
    bundles: Mapped[list["Bundle"]] = relationship(back_populates="network")
