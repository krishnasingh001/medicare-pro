#!/usr/bin/env bash
echo "========================================================"
echo "  Starting MediCare Pro Management System"
echo "========================================================"
echo ""

if [ ! -f "medicare.db" ]; then
    echo "[INFO] Database not found. Initializing demo data..."
    python3 seed.py --reset
fi

echo "[INFO] Starting Flask Server on http://127.0.0.1:5000..."
echo "[INFO] Demo Credentials: admin / admin123  or  staff / staff123"
echo ""
python3 app.py
