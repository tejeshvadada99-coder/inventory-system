"""
main.py
-------
The entry point. This is the file you run: `uvicorn app.main:app --reload`

What it does, in order:
  1. Creates all database tables (if they don't already exist).
  2. Upgrades an existing database with the new customer-role columns
     (migrations.py - safe to run on every start).
  3. Creates the first admin account from .env, if no admin exists yet.
  4. Registers every router (auth, admin, employee, customer, chatbot).
  5. Mounts the static folder (CSS/JS/QR codes) and serves the HTML pages.

Page routes (return HTML, for the browser):
  GET /                    -> homepage: Admin / Employee / Customer sign-in + register, chat
  GET /admin/dashboard      -> admin dashboard page
  GET /employee/dashboard   -> employee dashboard page
  GET /customer/dashboard   -> customer dashboard page

API routes (return JSON, used by the page's JavaScript):
  /auth/login, /auth/register, /admin/*, /employee/*, /customer/*, /chat  (see the respective router files)
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database import Base, engine, SessionLocal
from app.models import User, RoleEnum
from app.auth import hash_password
from app.config import settings
from app.migrations import run_light_migrations
from app.routers import auth_routes, admin, employee, customer, chatbot_routes

# 1. Create tables (new databases get everything), then 2. upgrade existing ones
Base.metadata.create_all(bind=engine)
run_light_migrations()

# 3. Seed the first admin account if none exists yet
def seed_first_admin():
    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == RoleEnum.admin).first()
        if not admin_exists:
            db.add(User(
                full_name="Administrator",
                username=settings.FIRST_ADMIN_USERNAME,
                email=settings.FIRST_ADMIN_EMAIL,
                hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                role=RoleEnum.admin,
            ))
            db.commit()
            print(f"[startup] Created first admin account: {settings.FIRST_ADMIN_USERNAME}")
    finally:
        db.close()

seed_first_admin()

app = FastAPI(title="Inventory Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Register API routers
app.include_router(auth_routes.router)
app.include_router(admin.router)
app.include_router(employee.router)
app.include_router(customer.router)
app.include_router(chatbot_routes.router)

# 5. Static files + HTML templates
BASE_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.get("/")
def homepage(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "store_name": settings.STORE_NAME}
    )


@app.get("/admin/dashboard")
def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})


@app.get("/employee/dashboard")
def employee_dashboard(request: Request):
    return templates.TemplateResponse("employee_dashboard.html", {"request": request})


@app.get("/customer/dashboard")
def customer_dashboard(request: Request):
    return templates.TemplateResponse(
        "customer_dashboard.html", {"request": request, "store_name": settings.STORE_NAME}
    )
