
import os
from dotenv import load_dotenv

# Load environment variables from the project-root .env file
load_dotenv()


class Settings:

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inventory_db"
    )

    # JWT authentication
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "insecure_dev_secret_change_me"
    )
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 120)
    )

    # Email configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME: str = os.getenv(
        "SMTP_FROM_NAME",
        "Inventory Store"
    )

    # Customer verification
    CUSTOMER_VERIFICATION_EXPIRE_MINUTES: int = int(
        os.getenv("CUSTOMER_VERIFICATION_EXPIRE_MINUTES", 10)
    )

    CUSTOMER_VERIFICATION_MAX_ATTEMPTS: int = int(
        os.getenv("CUSTOMER_VERIFICATION_MAX_ATTEMPTS", 5)
    )

    # Customer password reset
    CUSTOMER_PASSWORD_RESET_EXPIRE_MINUTES: int = int(
        os.getenv("CUSTOMER_PASSWORD_RESET_EXPIRE_MINUTES", 15)
    )

    # First admin account
    FIRST_ADMIN_USERNAME: str = os.getenv(
        "FIRST_ADMIN_USERNAME",
        "admin"
    )
    FIRST_ADMIN_PASSWORD: str = os.getenv(
        "FIRST_ADMIN_PASSWORD",
        "admin123"
    )
    FIRST_ADMIN_EMAIL: str = os.getenv(
        "FIRST_ADMIN_EMAIL",
        "admin@example.com"
    )

    # Store information
    STORE_NAME: str = os.getenv(
        "STORE_NAME",
        "GLOBAL STORE"
    )

    STORE_OPEN_TIME: str = os.getenv(
        "STORE_OPEN_TIME",
        "09:00"
    )

    STORE_CLOSE_TIME: str = os.getenv(
        "STORE_CLOSE_TIME",
        "21:00"
    )


settings = Settings()
