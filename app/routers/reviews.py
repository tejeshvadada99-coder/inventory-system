
"""
app/routers/reviews.py
----------------------
Product review management.

Features:
- Verified purchase reviews
- Customer review submission
- Customer review editing and deletion
- Public approved reviews
- Admin review moderation

Only customers who purchased a product can review it.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    Customer,
    Product,
    Bill,
    Sale,
    ProductReview,
    User,
)
from app.auth import get_current_customer, require_admin


router = APIRouter(
    prefix="/reviews",
    tags=["Product Reviews"]
)


# --------------------------------------------------
# Request schemas
# --------------------------------------------------

class ReviewCreate(BaseModel):
    product_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=3, max_length=1000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, min_length=3, max_length=1000)


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def serialize_review(review):
    customer_name = (
        review.customer.name
        if review.customer
        else "Customer"
    )

    return {
        "id": review.id,
        "product_id": review.product_id,
        "product_name": (
            review.product.name
            if review.product
            else "Product unavailable"
        ),
        "customer_id": review.customer_id,
        "customer_name": customer_name,
        "rating": review.rating,
        "comment": review.comment,
        "is_verified_purchase": review.is_verified_purchase,
        "is_approved": review.is_approved,
        "created_at": (
            review.created_at.isoformat()
            if review.created_at
            else None
        )
    }


def has_purchased_product(
    db: Session,
    customer_id: int,
    product_id: int
) -> bool:
    """
    Check whether the customer has purchased this product.

    Uses employee-created bills and sale records.
    """

    purchase = (
        db.query(Sale.id)
        .join(Bill, Sale.bill_id == Bill.id)
        .filter(
            Bill.customer_id == customer_id,
            Sale.product_id == product_id
        )
        .first()
    )

    return purchase is not None


def get_review_or_404(
    db: Session,
    review_id: int
):
    review = (
        db.query(ProductReview)
        .options(
            joinedload(ProductReview.customer),
            joinedload(ProductReview.product)
        )
        .filter(ProductReview.id == review_id)
        .first()
    )

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found."
        )

    return review


# --------------------------------------------------
# Submit a review
# --------------------------------------------------

@router.post(
    "",
    status_code=status.HTTP_201_CREATED
)
def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Submit a review for a product purchased by the customer.
    """

    if not current_customer.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is disabled."
        )

    product = db.query(Product).filter(
        Product.id == payload.product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found."
        )

    if not has_purchased_product(
        db,
        current_customer.id,
        payload.product_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You can review only products you have purchased."
        )

    existing_review = db.query(ProductReview).filter(
        ProductReview.customer_id == current_customer.id,
        ProductReview.product_id == payload.product_id
    ).first()

    if existing_review:
        raise HTTPException(
            status_code=409,
            detail="You have already reviewed this product."
        )

    review = ProductReview(
        customer_id=current_customer.id,
        product_id=payload.product_id,
        rating=payload.rating,
        comment=payload.comment.strip(),
        is_verified_purchase=True,
        is_approved=False
    )

    try:
        db.add(review)
        db.commit()
        db.refresh(review)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to submit review."
        )

    return {
        "message": "Review submitted successfully. It will appear after admin approval.",
        "review": serialize_review(
            get_review_or_404(db, review.id)
        )
    }


# --------------------------------------------------
# Public approved product reviews
# --------------------------------------------------

@router.get("/product/{product_id}")
def get_product_reviews(
    product_id: int,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Display approved and verified-purchase reviews.
    """

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found."
        )

    query = db.query(ProductReview).filter(
        ProductReview.product_id == product_id,
        ProductReview.is_approved.is_(True),
        ProductReview.is_verified_purchase.is_(True)
    )

    total_reviews = query.count()

    average_rating = db.query(
        func.avg(ProductReview.rating)
    ).filter(
        ProductReview.product_id == product_id,
        ProductReview.is_approved.is_(True),
        ProductReview.is_verified_purchase.is_(True)
    ).scalar()

    reviews = (
        query
        .options(
            joinedload(ProductReview.customer),
            joinedload(ProductReview.product)
        )
        .order_by(ProductReview.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "product_id": product_id,
        "product_name": product.name,
        "total_reviews": total_reviews,
        "average_rating": round(float(average_rating or 0), 2),
        "page": page,
        "limit": limit,
        "reviews": [
            serialize_review(review)
            for review in reviews
        ]
    }


# --------------------------------------------------
# Customer's own reviews
# --------------------------------------------------

@router.get("/my-reviews")
def get_my_reviews(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Display reviews submitted by the logged-in customer.
    """

    reviews = (
        db.query(ProductReview)
        .options(
            joinedload(ProductReview.customer),
            joinedload(ProductReview.product)
        )
        .filter(
            ProductReview.customer_id == current_customer.id
        )
        .order_by(ProductReview.created_at.desc())
        .all()
    )

    return {
        "total_reviews": len(reviews),
        "reviews": [
            serialize_review(review)
            for review in reviews
        ]
    }


# --------------------------------------------------
# Update own pending review
# --------------------------------------------------

@router.patch("/{review_id}")
def update_review(
    review_id: int,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Customers can edit their own pending reviews.
    """

    review = db.query(ProductReview).filter(
        ProductReview.id == review_id,
        ProductReview.customer_id == current_customer.id
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found."
        )

    if review.is_approved:
        raise HTTPException(
            status_code=403,
            detail="Approved reviews cannot be edited."
        )

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update."
        )

    for field, value in updates.items():
        if field == "comment" and value is not None:
            value = value.strip()

        setattr(review, field, value)

    # A changed review must be approved again.
    review.is_approved = False

    try:
        db.commit()
        db.refresh(review)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to update review."
        )

    return {
        "message": "Review updated. It requires admin approval again.",
        "review_id": review.id
    }


# --------------------------------------------------
# Delete own pending review
# --------------------------------------------------

@router.delete("/{review_id}")
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Customers can delete their own pending reviews.
    """

    review = db.query(ProductReview).filter(
        ProductReview.id == review_id,
        ProductReview.customer_id == current_customer.id
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found."
        )

    if review.is_approved:
        raise HTTPException(
            status_code=403,
            detail="Approved reviews cannot be deleted through this endpoint."
        )

    try:
        db.delete(review)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to delete review."
        )

    return {
        "message": "Review deleted successfully."
    }


# --------------------------------------------------
# Admin: list reviews
# --------------------------------------------------

@router.get("/admin/all")
def admin_get_reviews(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Admin can view all submitted reviews.
    """

    query = db.query(ProductReview)

    total_reviews = query.count()

    reviews = (
        query
        .options(
            joinedload(ProductReview.customer),
            joinedload(ProductReview.product)
        )
        .order_by(ProductReview.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "total_reviews": total_reviews,
        "page": page,
        "limit": limit,
        "reviews": [
            serialize_review(review)
            for review in reviews
        ]
    }


# --------------------------------------------------
# Admin: approve review
# --------------------------------------------------

@router.patch("/admin/{review_id}/approve")
def approve_review(
    review_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Approve a verified-purchase review.
    """

    review = db.query(ProductReview).filter(
        ProductReview.id == review_id
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found."
        )

    if not review.is_verified_purchase:
        raise HTTPException(
            status_code=403,
            detail="Only verified-purchase reviews can be approved."
        )

    review.is_approved = True

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to approve review."
        )

    return {
        "message": "Review approved successfully."
    }


# --------------------------------------------------
# Admin: reject review
# --------------------------------------------------

@router.patch("/admin/{review_id}/reject")
def reject_review(
    review_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Reject a customer review.
    """

    review = db.query(ProductReview).filter(
        ProductReview.id == review_id
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found."
        )

    review.is_approved = False

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to reject review."
        )

    return {
        "message": "Review rejected successfully."
    }
