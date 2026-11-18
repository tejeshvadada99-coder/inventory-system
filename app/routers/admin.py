from sqlalchemy import exists

@router.delete("/customers/non-members")
def delete_nonmember_customers(
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin),   # use the same dependency as your other admin routes
):
    has_bill = exists().where(Bill.customer_id == Customer.id)
    query = db.query(Customer).filter(Customer.user_id.is_(None), ~has_bill)

    count = query.count()
    if not confirm:
        return {"would_delete": count, "message": "Add ?confirm=true to delete."}

    query.delete(synchronize_session=False)
    db.commit()
    return {"deleted": count}
