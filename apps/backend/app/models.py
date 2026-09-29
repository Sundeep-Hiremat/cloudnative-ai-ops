import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from apps.backend.app.database import Base


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_name = Column(String(255), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    total_price = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, PROCESSING, COMPLETED, CANCELLED
    created_at = Column(DateTime(timezone=True), default=utc_now)
