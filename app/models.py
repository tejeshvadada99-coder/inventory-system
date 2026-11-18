
import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    Enum,
    Text,
    Boolean,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ============================================================
# ENUMS
# ============================================================

class RoleEnum(str, enum.Enum):
    admin = "admin"
    employee = "employee"


class VerificationType(str, enum.Enum):
    email = "email"
    mobile = "mobile"


# ============================================================
# ADMIN AND EMPLOYEE USERS
# ============================================================

class User(Base):
    """Login account for admins and employees."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    username = Column(String(60), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    role = Column(
        Enum(RoleEnum),
        nullable=False,
        default=RoleEnum.employee
    )

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    audit_logs = relationship(
        "AuditLog",
        back_populates="user"
    )


# ============================================================
# PRODUCT CATEGORIES
# ============================================================

class Category(Base):
    """Product categories, managed only by admins."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    products = relationship(
        "Product",
        back_populates="category"
    )


# ============================================================
# PRODUCTS
# ============================================================

class Product(Base):
    """A stock item belonging to a category."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    sku = Column(String(60), unique=True, nullable=False)

    category_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=False
    )

    price = Column(Float, nullable=False)
    quantity_in_stock = Column(Integer, default=0)
    reorder_level = Column(Integer, default=5)

    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship(
        "Category",
        back_populates="products"
    )

    sale_lines = relationship(
        "Sale",
        back_populates="product"
    )

    reviews = relationship(
        "ProductReview",
        back_populates="product",
        cascade="all, delete-orphan"
    )


# ============================================================
# CUSTOMERS
# ============================================================

class Customer(Base):
    """
    Customer information and optional customer login account.

    Existing billing customers can continue without an account.
    Registered customers can log in and view their purchase history.
    """

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)

    # Existing billing fields
    name = Column(String(120), nullable=False)

    mobile_number = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )

    email = Column(
        String(120),
        unique=True,
        nullable=True,
        index=True
    )

    # Customer registration fields
    hashed_password = Column(String(255), nullable=True)

    address = Column(Text, nullable=True)

    # Account and verification status
    is_active = Column(Boolean, default=True, nullable=False)

    email_verified = Column(Boolean, default=False, nullable=False)

    mobile_verified = Column(Boolean, default=False, nullable=False)

    # Loyalty points summary
    loyalty_points = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Existing billing relationship
    bills = relationship(
        "Bill",
        back_populates="customer"
    )

    # Customer verification
    verifications = relationship(
        "CustomerVerification",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    # Product reviews
    reviews = relationship(
        "ProductReview",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    # Loyalty transactions
    loyalty_transactions = relationship(
        "LoyaltyTransaction",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    # Notifications
    notifications = relationship(
        "Notification",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    # Customer activity logs
    audit_logs = relationship(
        "AuditLog",
        back_populates="customer"
    )


# ============================================================
# CUSTOMER EMAIL AND MOBILE VERIFICATION
# ============================================================

class CustomerVerification(Base):
    """
    Stores customer verification tokens or OTP hashes.

    Never store raw OTPs or verification secrets.
    """

    __tablename__ = "customer_verifications"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False,
        index=True
    )

    verification_type = Column(
        Enum(VerificationType),
        nullable=False
    )

    token_hash = Column(String(255), nullable=False)

    expires_at = Column(DateTime, nullable=False)

    verified_at = Column(DateTime, nullable=True)

    attempts = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship(
        "Customer",
        back_populates="verifications"
    )


# ============================================================
# BILLING
# ============================================================

class Bill(Base):
    """One billing transaction containing multiple sale items."""

    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False
    )

    created_by_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    total_amount = Column(Float, nullable=False, default=0.0)

    qr_code_path = Column(String(255), nullable=True)

    email_sent = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship(
        "Customer",
        back_populates="bills"
    )

    created_by = relationship("User")

    sale_lines = relationship(
        "Sale",
        back_populates="bill",
        cascade="all, delete-orphan"
    )

    loyalty_transactions = relationship(
        "LoyaltyTransaction",
        back_populates="bill"
    )


# ============================================================
# SALES
# ============================================================

class Sale(Base):
    """One product line within a bill."""

    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)

    bill_id = Column(
        Integer,
        ForeignKey("bills.id"),
        nullable=False
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    quantity = Column(Integer, nullable=False)

    unit_price = Column(Float, nullable=False)

    line_total = Column(Float, nullable=False)

    bill = relationship(
        "Bill",
        back_populates="sale_lines"
    )

    product = relationship(
        "Product",
        back_populates="sale_lines"
    )

    review = relationship(
        "ProductReview",
        back_populates="sale",
        uselist=False
    )


# ============================================================
# PRODUCT REVIEWS AND RATINGS
# ============================================================

class ProductReview(Base):
    """
    Product review submitted by a customer.

    A review must reference an actual sale line.
    The application must verify that the sale belongs to
    the customer and contains the reviewed product.
    """

    __tablename__ = "product_reviews"

    __table_args__ = (
        UniqueConstraint(
            "sale_id",
            name="uq_product_review_sale"
        ),
        Index(
            "ix_product_review_product_rating",
            "product_id",
            "rating"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False,
        index=True
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )

    sale_id = Column(
        Integer,
        ForeignKey("sales.id"),
        nullable=False,
        unique=True
    )

    rating = Column(Integer, nullable=False)

    review_text = Column(Text, nullable=True)

    is_verified_purchase = Column(
        Boolean,
        default=True,
        nullable=False
    )

    is_approved = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    customer = relationship(
        "Customer",
        back_populates="reviews"
    )

    product = relationship(
        "Product",
        back_populates="reviews"
    )

    sale = relationship(
        "Sale",
        back_populates="review"
    )


# ============================================================
# LOYALTY AND REWARD TRANSACTIONS
# ============================================================

class LoyaltyTransaction(Base):
    """
    Records earned, redeemed and adjusted loyalty points.

    points should be positive for earned points and
    negative for redeemed points.
    """

    __tablename__ = "loyalty_transactions"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False,
        index=True
    )

    bill_id = Column(
        Integer,
        ForeignKey("bills.id"),
        nullable=True
    )

    transaction_type = Column(
        String(30),
        nullable=False
    )

    points = Column(Integer, nullable=False)

    description = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship(
        "Customer",
        back_populates="loyalty_transactions"
    )

    bill = relationship(
        "Bill",
        back_populates="loyalty_transactions"
    )


# ============================================================
# CUSTOMER NOTIFICATIONS
# ============================================================

class Notification(Base):
    """Stores customer notifications."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False,
        index=True
    )

    title = Column(String(150), nullable=False)

    message = Column(Text, nullable=False)

    notification_type = Column(
        String(50),
        default="general"
    )

    is_read = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship(
        "Customer",
        back_populates="notifications"
    )


# ============================================================
# AUDIT LOGS
# ============================================================

class AuditLog(Base):
    """
    Records important activities performed by users or customers.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=True,
        index=True
    )

    action = Column(String(120), nullable=False)

    description = Column(Text, nullable=True)

    ip_address = Column(String(45), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship(
        "User",
        back_populates="audit_logs"
    )

    customer = relationship(
        "Customer",
        back_populates="audit_logs"
    )


# ============================================================
# OFFERS
# ============================================================

class Offer(Base):
    """Daily and ongoing offers managed by admins."""

    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(150), nullable=False)

    description = Column(Text, nullable=False)

    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
