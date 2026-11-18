"""
config.py
---------
Loads every setting from the .env file into one place (a `settings` object)
so the rest of the app never touches os.environ directly.

Why this file exists:
Every other file that needs a secret, a DB URL, or store info imports
`settings` from here instead of reading .env itself. That means there is
exactly one place to change when you move from your laptop to a real server.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file in the project root into the environment


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/inventory_db"
    )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure_dev_secret_change_me")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 120))

    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Inventory Store")
    SMTP_TIMEOUT: int = int(os.getenv("SMTP_TIMEOUT", 10))  # seconds; stops a blocked SMTP port from hanging the app

    FIRST_ADMIN_USERNAME: str = os.getenv("FIRST_ADMIN_USERNAME", "admin")
    FIRST_ADMIN_PASSWORD: str = os.getenv("FIRST_ADMIN_PASSWORD", "admin123")
    FIRST_ADMIN_EMAIL: str = os.getenv("FIRST_ADMIN_EMAIL", "admin@example.com")

    STORE_NAME: str = os.getenv("STORE_NAME", "Your Store")
    STORE_OPEN_TIME: str = os.getenv("STORE_OPEN_TIME", "09:00")
    STORE_CLOSE_TIME: str = os.getenv("STORE_CLOSE_TIME", "21:00")

    # Loyalty programme: 1 point for every X spent; tier thresholds in points.
    LOYALTY_SPEND_PER_POINT: float = float(os.getenv("LOYALTY_SPEND_PER_POINT", 100))
    SILVER_POINTS: int = int(os.getenv("SILVER_POINTS", 100))
    GOLD_POINTS: int = int(os.getenv("GOLD_POINTS", 500))


settings = Settings()
