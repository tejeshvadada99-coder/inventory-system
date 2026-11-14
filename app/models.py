
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, DateTime, Enum, Text, Boolean
)
from sqlalchemy.orm import relationship

from app.database import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    employee = "employee"


class User(Base):
    """Login account for admins and employees."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    username = Column(String(60), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.employee)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Category(Base):
    """Product categories, managed only by admins."""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    products = relationship("Product", back_populates="category")


class Product(Base):
    """A stock item. Belongs to a category, has a live quantity for stock tracking."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    sku = Column(String(60), unique=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    price = Column(Float, nullable=False)
    quantity_in_stock = Column(Integer, default=0)
    reorder_level = Column(Integer, default=5)  # chatbot warns when stock <= this
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    sale_lines = relationship("Sale", back_populates="product")


class Customer(Base):
    """A customer record, created/reused automatically at billing time."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    mobile_number = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(120), nullable=True)

    bills = relationship("Bill", back_populates="customer")


class Bill(Base):
    """One billing transaction (a receipt). Contains many Sale line items."""
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # which employee billed it
    total_amount = Column(Float, nullable=False, default=0.0)
    qr_code_path = Column(String(255), nullable=True)
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="bills")
    created_by = relationship("User")
    sale_lines = relationship("Sale", back_populates="bill", cascade="all, delete-orphan")


class Sale(Base):
    """One line item within a Bill: a product, quantity, and price at time of sale."""
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)  # snapshot of price at sale time
    line_total = Column(Float, nullable=False)

    bill = relationship("Bill", back_populates="sale_lines")
    product = relationship("Product", back_populates="sale_lines")


class Offer(Base):
    """Daily/ongoing offers. Admins manage these; the chatbot reads them."""
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
