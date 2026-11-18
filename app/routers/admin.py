"""
routers/admin.py
------------------
Everything gated behind `Depends(require_admin)` — only accounts with
role="admin" can call these. Covers the 4 areas from the brief:

  Employees : POST/GET/DELETE /admin/employees
  Category  : POST/GET/DELETE /admin/categories
  Product   : POST/GET/PUT/DELETE /admin/products
  Sales     : GET /admin/sales  (read-only report of every bill)

Also includes Offers management (offers feed the chatbot and can be members-only),
a read-only Customers list, and email alerts to opted-in members when a new
offer is published or an out-of-stock product is restocked.
"""
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin, hash_password
from app.models import User, Category, Product, Bill, Offer, Customer, RoleEnum
from app.utils.alerts import get_alert_recipients, send_alerts
from app.schemas import (
    UserCreate, UserOut, CategoryCreate, CategoryOut,
    ProductCreate, ProductUpdate, ProductOut, BillOut,
    OfferCreate, OfferOut,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------- Employees ----------
@router.post("/employees", response_model=UserOut)
def create_employee(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(400, "Username already taken")
    if db.query(User).filter(func.lower(User.email) == payload.email.lower()).first():
        raise HTTPException(400, "Email already in use")
    user = User(
        full_name=payload.full_name,
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/employees", response_model=List[UserOut])
def list_employees(db: Session = Depends(get_db)):
    return db.query(User).filter(User.role == RoleEnum.employee).all()


@router.delete("/employees/{user_id}")
def deactivate_employee(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Employee not found")
    user.is_active = False
    db.commit()
    return {"message": "Employee deactivated"}


# ---------- Categories ----------
@router.post("/categories", response_model=CategoryOut)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    if db.query(Category).filter(Category.name == payload.name).first():
        raise HTTPException(400, "Category already exists")
    category = Category(**payload.dict())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/categories", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(404, "Category not found")
    db.delete(category)
    db.commit()
    return {"message": "Category deleted"}


# ---------- Products ----------
@router.post("/products", response_model=ProductOut)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.sku == payload.sku).first():
        raise HTTPException(400, "SKU already exists")
    product = Product(**payload.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/products", response_model=List[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    was_out_of_stock = product.quantity_in_stock <= 0
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)

    # Back in stock -> tell members who opted in (emailed in the background).
    if was_out_of_stock and product.quantity_in_stock > 0:
        background_tasks.add_task(
            send_alerts, get_alert_recipients(db), "Back in stock",
            f"Good news - {product.name} is available again ({product.quantity_in_stock} in stock).",
        )
    return product


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}


# ---------- Sales (read-only report) ----------
@router.get("/sales", response_model=List[BillOut])
def list_sales(db: Session = Depends(get_db)):
    return db.query(Bill).order_by(Bill.created_at.desc()).all()


# ---------- Customers (read-only list with loyalty info) ----------
@router.get("/customers")
def list_customers(db: Session = Depends(get_db)):
    spent = dict(
        db.query(Bill.customer_id, func.coalesce(func.sum(Bill.total_amount), 0.0))
        .group_by(Bill.customer_id).all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "mobile_number": c.mobile_number,
            "email": c.email,
            "is_member": c.is_member,
            "loyalty_points": c.loyalty_points,
            "total_spent": float(spent.get(c.id, 0.0)),
        }
        for c in db.query(Customer).order_by(Customer.id.desc()).all()
    ]


# ---------- Offers (feeds the chatbot) ----------
@router.post("/offers", response_model=OfferOut)
def create_offer(payload: OfferCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    offer = Offer(**payload.dict())
    db.add(offer)
    db.commit()
    db.refresh(offer)

    if offer.active:
        label = "Members-only offer" if offer.members_only else "New offer"
        background_tasks.add_task(
            send_alerts, get_alert_recipients(db), label, f"{offer.title}\n{offer.description}"
        )
    return offer


@router.get("/offers", response_model=List[OfferOut])
def list_offers(db: Session = Depends(get_db)):
    return db.query(Offer).all()


@router.delete("/offers/{offer_id}")
def delete_offer(offer_id: int, db: Session = Depends(get_db)):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(404, "Offer not found")
    db.delete(offer)
    db.commit()
    return {"message": "Offer deleted"}
