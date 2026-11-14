
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database import Base, engine, SessionLocal
from app.models import User, RoleEnum
from app.auth import hash_password
from app.config import settings
from app.routers import auth_routes, admin, employee, chatbot_routes

# 1. Create tables
Base.metadata.create_all(bind=engine)

# 2. Seed the first admin account if none exists yet
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

# 3. Register API routers
app.include_router(auth_routes.router)
app.include_router(admin.router)
app.include_router(employee.router)
app.include_router(chatbot_routes.router)

# 4. Static files + HTML templates
BASE_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.get("/")
def homepage(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"store_name": settings.STORE_NAME}
    )


@app.get("/admin/dashboard")
def admin_dashboard(request: Request):
    return templates.TemplateResponse(request, "admin_dashboard.html", {})


@app.get("/employee/dashboard")
def employee_dashboard(request: Request):
    return templates.TemplateResponse(request, "employee_dashboard.html", {})