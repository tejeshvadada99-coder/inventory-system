
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.auth import require_admin, hash_password

from app.models import (
    User,
    Category,
    Product,
    Customer,
    ProductReview,
    Bill,
    Sale,
    Offer,
    RoleEnum,
)

from app.schemas import (
    UserCreate,
    UserOut,
    CategoryCreate,
    CategoryOut,
    ProductCreate,
    ProductUpdate,
    ProductOut,
    CustomerOut,
    ProductReviewOut,
    BillOut,
    OfferCreate,
    OfferOut,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)]
)


# ==================================================
# EMPLOYEES
# ==================================================

@router.post("/employees", response_model=UserOut)
def create_employee(
    payload: UserCreate,
    db: Session = Depends(get_db)
):
    if db.query(User).filter(
        User.username == payload.username
    ).first():
        raise HTTPException(400, "Username already taken")

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
    return db.query(User).filter(
        User.role == RoleEnum.employee
    ).all()


@router.delete("/employees/{user_id}")
def deactivate_employee(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(404, "Employee not found")

    user.is_active = False
    db.commit()

    return {"message": "Employee deactivated"}


# ==================================================
# CUSTOMERS
# ==================================================

@router.get("/customers", response_model=List[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(
        Customer.created_at.desc()
    ).all()


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(404, "Customer not found")

    return customer


@router.delete("/customers/{customer_id}")
def deactivate_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(404, "Customer not found")

    customer.is_active = False
    db.commit()

    return {"message": "Customer account deactivated"}


# ==================================================
# CATEGORIES
# ==================================================

@router.post("/categories", response_model=CategoryOut)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db)
):
    if db.query(Category).filter(
        Category.name == payload.name
    ).first():
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
def delete_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(404, "Category not found")

    product_count = db.query(Product).filter(
        Product.category_id == category_id
    ).count()

    if product_count > 0:
        raise HTTPException(
            400,
            f"Can't delete '{category.name}' — "
            f"{product_count} product(s) still use it. "
            "Delete or move those products first."
        )

    db.delete(category)
    db.commit()

    return {"message": "Category deleted"}


# ==================================================
# PRODUCTS
# ==================================================

@router.post("/products", response_model=ProductOut)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db)
):
    if db.query(Product).filter(
        Product.sku == payload.sku
    ).first():
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
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(404, "Product not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return product


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(404, "Product not found")

    sale_count = db.query(Sale).filter(
        Sale.product_id == product_id
    ).count()

    if sale_count > 0:
        raise HTTPException(
            400,
            f"Can't delete '{product.name}' — "
            f"it's already used in {sale_count} sale(s). "
            "Set its stock to 0 instead of deleting it, "
            "to keep sales history intact."
        )

    try:
        db.delete(product)
        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            400,
            f"Can't delete '{product.name}' — "
            "it's still referenced elsewhere."
        )

    return {"message": "Product deleted"}


# ==================================================
# PRODUCT REVIEW MODERATION
# ==================================================

@router.get("/reviews", response_model=List[ProductReviewOut])
def list_product_reviews(db: Session = Depends(get_db)):
    return db.query(ProductReview).order_by(
        ProductReview.created_at.desc()
    ).all()


@router.patch("/reviews/{review_id}/approve")
def approve_product_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    review = db.query(ProductReview).filter(
        ProductReview.id == review_id
    ).first()

    if not review:
        raise HTTPException(404, "Review not found")

    if not review.is_verified_purchase:
        raise HTTPException(
            400,
            "Only verified-purchase reviews can be approved."
        )

    review.is_approved = True
    db.commit()

    return {"message": "Product review approved"}


@router.patch("/reviews/{review_id}/reject")
def reject_product_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    review = db.query(ProductReview).filter(
        ProductReview.id == review_id
    ).first()

    if not review:
        raise HTTPException(404, "Review not found")

    review.is_approved = False
    db.commit()

    return {"message": "Product review rejected"}


# ==================================================
# SALES REPORT
# ==================================================

@router.get("/sales", response_model=List[BillOut])
def list_sales(db: Session = Depends(get_db)):
    return db.query(Bill).order_by(
        Bill.created_at.desc()
    ).all()


# ==================================================
# OFFERS
# ==================================================

@router.post("/offers", response_model=OfferOut)
def create_offer(
    payload: OfferCreate,
    db: Session = Depends(get_db)
):
    offer = Offer(**payload.dict())

    db.add(offer)
    db.commit()
    db.refresh(offer)

    return offer


@router.get("/offers", response_model=List[OfferOut])
def list_offers(db: Session = Depends(get_db)):
    return db.query(Offer).all()


@router.delete("/offers/{offer_id}")
def delete_offer(
    offer_id: int,
    db: Session = Depends(get_db)
):
    offer = db.query(Offer).filter(
        Offer.id == offer_id
    ).first()

    if not offer:
        raise HTTPException(404, "Offer not found")

    db.delete(offer)
    db.commit()

    return {"message": "Offer deleted"}
