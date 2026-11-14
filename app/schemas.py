
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
    username: str
    password: str


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

    class Config:
        from_attributes = True


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


class OfferOut(BaseModel):
    id: int
    title: str
    description: str
    active: bool

    class Config:
        from_attributes = True


# ---------- Chatbot ----------
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
