"""
schemas.py
----------
Pydantic "schemas" define the shape of data going IN to the API (what a
request body must look like) and OUT of the API (what a JSON response looks
like). They are separate from models.py (the database tables) on purpose:
a model has internal fields (like hashed_password) that should never be
sent back to a browser — the schema is the filter that decides what's public.

Naming convention used throughout:
  XCreate  -> fields required to create a new X
  XOut     -> fields returned to the client when reading X
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

from app.models import RoleEnum


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class LoginRequest(BaseModel):
    username: str  # staff: username. Customers: email or mobile number also work.
    password: str


class CustomerRegister(BaseModel):
    full_name: str
    mobile_number: str
    email: EmailStr
    password: str
    confirm_password: str


# ---------- User (employee/admin) ----------
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


# ---------- Category ----------
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Product ----------
class ProductCreate(BaseModel):
    name: str
    sku: str
    category_id: int
    price: float
    quantity_in_stock: int = 0
    reorder_level: int = 5


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    quantity_in_stock: Optional[int] = None
    reorder_level: Optional[int] = None
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


# ---------- Customer ----------
class CustomerCreate(BaseModel):
    name: str
    mobile_number: str
    email: Optional[EmailStr] = None


class CustomerOut(BaseModel):
    id: int
    name: str
    mobile_number: str
    email: Optional[EmailStr] = None
    loyalty_points: int = 0
    is_member: bool = False

    class Config:
        from_attributes = True


class CustomerUpdate(BaseModel):
    """What staff may fix on a customer who has NOT registered an account."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class ProfileUpdate(BaseModel):
    """What a customer may change on their own profile (mobile is read-only)."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    alerts_enabled: Optional[bool] = None


# ---------- Billing ----------
class BillLineItem(BaseModel):
    product_id: int
    quantity: int


class BillCreate(BaseModel):
    customer_name: str
    customer_mobile: str
    customer_email: Optional[EmailStr] = None
    items: List[BillLineItem]


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
    points_earned: int = 0
    created_at: datetime
    customer: CustomerOut
    sale_lines: List[SaleLineOut]

    class Config:
        from_attributes = True


# ---------- Offer ----------
class OfferCreate(BaseModel):
    title: str
    description: str
    active: bool = True
    members_only: bool = False


class OfferOut(BaseModel):
    id: int
    title: str
    description: str
    active: bool
    members_only: bool = False

    class Config:
        from_attributes = True


# ---------- Chatbot ----------
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
