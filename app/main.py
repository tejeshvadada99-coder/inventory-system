
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database import init_db, SessionLocal
from app.models import User, RoleEnum
from app.auth import hash_password
from app.config import settings
from app.routers import (
    auth_routes,
    admin,
    employee,
    chatbot_routes,
    customer_auth,
    customers,
    reviews,
    loyalty,
)

# 1. Initialize database
init_db()


# 2. Seed first admin
def seed_first_admin():
    db = SessionLocal()

    try:
        admin_exists = (
            db.query(User)
            .filter(User.role == RoleEnum.admin)
            .first()
        )

        if not admin_exists:
            db.add(
                User(
                    full_name="Administrator",
                    username=settings.FIRST_ADMIN_USERNAME,
                    email=settings.FIRST_ADMIN_EMAIL,
                    hashed_password=hash_password(
                        settings.FIRST_ADMIN_PASSWORD
                    ),
                    role=RoleEnum.admin,
                )
            )

            db.commit()
            print("[startup] First admin account created")

    finally:
        db.close()


seed_first_admin()


# 3. Create application
app = FastAPI(title="Inventory Management System")


# 4. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# 5. Register API routers
app.include_router(auth_routes.router)
app.include_router(admin.router)
app.include_router(employee.router)
app.include_router(chatbot_routes.router)
app.include_router(customer_auth.router)
app.include_router(customers.router)
app.include_router(reviews.router)
app.include_router(loyalty.router)


# 6. Static files and templates
BASE_DIR = os.path.dirname(__file__)

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static",
)

templates = Jinja2Templates(
    directory=os.path.join(BASE_DIR, "templates")
)


# 7. Homepage
@app.get("/")
def homepage(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"store_name": settings.STORE_NAME},
    )


# 8. Customer registration page
@app.get("/customer/register")
def customer_register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "customer_register.html",
        {"store_name": settings.STORE_NAME},
    )


# 9. Customer login page
@app.get("/customer/login")
def customer_login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "customer_login.html",
        {"store_name": settings.STORE_NAME},
    )


# 10. Customer dashboard page
@app.get("/customer/dashboard")
def customer_dashboard_page(request: Request):
    return templates.TemplateResponse(
        request,
        "customer_dashboard.html",
        {"store_name": settings.STORE_NAME},
    )


# 11. Admin dashboard
@app.get("/admin/dashboard")
def admin_dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {},
    )


# 12. Employee dashboard
@app.get("/employee/dashboard")
def employee_dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "employee_dashboard.html",
        {},
    )
