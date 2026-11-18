
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field

from app.models import RoleEnum, VerificationType


# ============================================================
# AUTHENTICATION
# ============================================================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class LoginRequest(BaseModel):
    username: str
    password: str


class CustomerLoginRequest(BaseModel):
    """
    Customers can log in using either email or mobile number.
    The backend must identify the customer securely.
    """
    identifier: str = Field(min_length=3, max_length=120)
    password: str


# ============================================================
# ADMIN AND EMPLOYEE USERS
# ============================================================

class UserCreate(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str
    role: RoleEnum = RoleEnum.employee


class UserOut(BaseModel):
    id: int
    full_name: str
    username: str
    email: EmailStr
    role: RoleEnum
    is_active: bool

    class Config:
        from_attributes = True


# ============================================================
# CATEGORY
# ============================================================

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================
# PRODUCT
# ============================================================

class ProductCreate(BaseModel):
    name: str
    sku: str
    category_id: int
    price: float = Field(gt=0)
    quantity_in_stock: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=5, ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    quantity_in_stock: Optional[int] = Field(default=None, ge=0)
    reorder_level: Optional[int] = Field(default=None, ge=0)
    category_id: Optional[int] = None


class ProductOut(BaseModel):
    id: int
    name: str
    sku: str
    category_id: int
    price: float
    quantity_in_stock: int
    reorder_level: int

    class Config:
        from_attributes = True


# ============================================================
# CUSTOMER - EXISTING BILLING SCHEMAS
# ============================================================

class CustomerCreate(BaseModel):
    """
    Used by the existing employee billing system.
    Does not create a customer login account.
    """
    name: str
    mobile_number: str
    email: Optional[EmailStr] = None


class CustomerOut(BaseModel):
    id: int
    name: str
    mobile_number: str
    email: Optional[EmailStr] = None

    class Config:
        from_attributes = True


# ============================================================
# CUSTOMER REGISTRATION
# ============================================================

class CustomerRegister(BaseModel):
    """New customer account registration."""

    name: str = Field(min_length=2, max_length=120)

    email: EmailStr

    mobile_number: str = Field(min_length=10, max_length=20)

    password: str = Field(min_length=8, max_length=128)

    confirm_password: str = Field(min_length=8, max_length=128)

    address: Optional[str] = Field(default=None, max_length=1000)


class CustomerRegistrationOut(BaseModel):
    """Safe registration response without sensitive information."""

    id: int
    name: str
    email: Optional[EmailStr] = None
    mobile_number: str
    email_verified: bool
    mobile_verified: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# CUSTOMER PROFILE
# ============================================================

class CustomerProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)

    mobile_number: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=20
    )

    address: Optional[str] = Field(default=None, max_length=1000)


class CustomerProfileOut(BaseModel):
    id: int
    name: str
    email: Optional[EmailStr] = None
    mobile_number: str
    address: Optional[str] = None

    email_verified: bool
    mobile_verified: bool
    is_active: bool

    loyalty_points: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# CUSTOMER EMAIL AND MOBILE VERIFICATION
# ============================================================

class VerificationRequest(BaseModel):
    verification_type: VerificationType


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class MobileVerificationRequest(BaseModel):
    mobile_number: str = Field(min_length=10, max_length=20)


class VerificationConfirm(BaseModel):
    verification_type: VerificationType

    # Verification code or token supplied to the customer.
    code: str = Field(min_length=6, max_length=255)


class VerificationResponse(BaseModel):
    message: str
    verification_type: VerificationType


# ============================================================
# CUSTOMER PASSWORD MANAGEMENT
# ============================================================

class CustomerPasswordChange(BaseModel):
    current_password: str

    new_password: str = Field(min_length=8, max_length=128)

    confirm_password: str = Field(min_length=8, max_length=128)


class CustomerPasswordResetRequest(BaseModel):
    email: EmailStr


class CustomerPasswordResetConfirm(BaseModel):
    token: str

    new_password: str = Field(min_length=8, max_length=128)

    confirm_password: str = Field(min_length=8, max_length=128)


# ============================================================
# BILLING
# ============================================================

class BillLineItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class BillCreate(BaseModel):
    customer_name: str
    customer_mobile: str
    customer_email: Optional[EmailStr] = None
    items: List[BillLineItem] = Field(min_length=1)


class SaleLineOut(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    line_total: float

    class Config:
        from_attributes = True


class BillOut(BaseModel):
    id: int
    total_amount: float
    email_sent: bool
    created_at: datetime
    customer: CustomerOut
    sale_lines: List[SaleLineOut]

    class Config:
        from_attributes = True


# ============================================================
# CUSTOMER PURCHASE HISTORY
# ============================================================

class CustomerPurchaseHistoryOut(BaseModel):
    customer: CustomerProfileOut
    bills: List[BillOut]
    total_purchases: int
    total_amount_spent: float

    class Config:
        from_attributes = True


# ============================================================
# PRODUCT REVIEWS AND RATINGS
# ============================================================

class ProductReviewCreate(BaseModel):
    """
    A review must be linked to an actual sale line.
    The backend must verify ownership and product identity.
    """
    sale_id: int

    rating: int = Field(ge=1, le=5)

    review_text: Optional[str] = Field(
        default=None,
        max_length=2000
    )


class ProductReviewUpdate(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)

    review_text: Optional[str] = Field(
        default=None,
        max_length=2000
    )


class ProductReviewOut(BaseModel):
    id: int
    customer_id: int
    product_id: int
    sale_id: int
    rating: int
    review_text: Optional[str] = None
    is_verified_purchase: bool
    is_approved: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductRatingSummary(BaseModel):
    product_id: int
    average_rating: float
    total_reviews: int


# ============================================================
# LOYALTY AND REWARDS
# ============================================================

class LoyaltyTransactionOut(BaseModel):
    id: int
    customer_id: int
    bill_id: Optional[int] = None
    transaction_type: str
    points: int
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerLoyaltyOut(BaseModel):
    customer_id: int
    total_points: int
    transactions: List[LoyaltyTransactionOut]


# ============================================================
# CUSTOMER NOTIFICATIONS
# ============================================================

class NotificationCreate(BaseModel):
    title: str
    message: str
    notification_type: str = "general"


class NotificationOut(BaseModel):
    id: int
    customer_id: int
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# AUDIT LOGS
# ============================================================

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    customer_id: Optional[int] = None
    action: str
    description: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# OFFERS
# ============================================================

class OfferCreate(BaseModel):
    title: str
    description: str
    active: bool = True


class OfferOut(BaseModel):
    id: int
    title: str
    description: str
    active: bool

    class Config:
        from_attributes = True


# ============================================================
# CHATBOT
# ============================================================

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
