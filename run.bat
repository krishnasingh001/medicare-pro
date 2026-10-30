@echo off
title MediCare Pro - Medical Store Management System
echo ========================================================
echo   Starting MediCare Pro Management System
echo ========================================================
echo.

if not exist "medicare.db" (
    echo [INFO] Database not found. Initializing and seeding demo data...
    python seed.py --reset
)

echo [INFO] Starting Flask Server on http://127.0.0.1:5000...
echo [INFO] Demo Credentials: admin / admin123  or  staff / staff123
echo.
python app.py
pause
