import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get('SECRET_KEY', 'medicare-pro-secret-key-2026-secure-development')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'medicare.db'))
    
    # Expiry alert thresholds (in days)
    EXPIRY_URGENT_DAYS = 30
    EXPIRY_WARNING_DAYS = 90
    
    # Low stock default threshold
    DEFAULT_MIN_STOCK = 10
    
    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # Pharmacy Metadata (for invoices & receipts)
    PHARMACY_NAME = "MediCare Pro Pharmacy"
    PHARMACY_TAGLINE = "Your Trusted Healthcare & Wellness Partner"
    PHARMACY_ADDRESS = "104 Healthcare Boulevard, Medical Enclave, City - 400001"
    PHARMACY_PHONE = "+91 98765 43210"
    PHARMACY_EMAIL = "support@medicarepro.local"
    PHARMACY_GSTIN = "27AABCM8901L1Z4"
    PHARMACY_DL = "DL-20B-MH-44589 / DL-21B-MH-44590"
