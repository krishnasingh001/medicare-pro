# MediCare Pro – Medical Store Management System

A complete, professional, full-stack **Medical Store Management System** tailored for a college mini project and ready for real-world deployment. Built with Python Flask, SQLite, and a modern, responsive Healthcare UI/UX design system (HTML5, Vanilla CSS3, JavaScript, Chart.js, and Font Awesome).

---

## 🏥 Key Features

### 1. Executive Dashboard & Live Analytics
- **8 Dynamic DB Statistics**: Active Medicines, Stock Units in Inventory, Low-Stock Medicines, Expiring in &le; 30 Days, Expired Batches (blocked), Today's Sales Revenue, Today's Purchases, and Total Sales Transactions.
- **Interactive Chart.js Visuals**: 7-day revenue trend line chart with smooth curves and gradient fill, plus therapeutic category distribution doughnut chart.
- **Urgent Alerts**: Immediate cards highlighting medicines needing reorder and batches approaching expiry.
- **Recent Counter Sales**: Quick transaction lookup with single-click receipt printing.

### 2. Medicine Inventory Management
- **Full CRUD Operations**: Create, view, edit, and deactivate medicines.
- **Complete Details**: Medicine name, unique system code (e.g., `MED-001`), generic salt composition, category, manufacturer, rack/shelf location, and minimum reorder stock level.
- **Batch-Level Tracking**: Multiple batches per medicine with distinct batch numbers, manufacturing dates, expiry dates, purchase cost, selling price, and quantities.
- **Stock Audit Trail**: Tracks every unit inward or outward (`PURCHASE`, `SALE`, `DAMAGE_REMOVAL`, `EXPIRED_REMOVAL`, `ADJUSTMENT`).
- **Search, Filtering & Pagination**: Filter by name, code, generic salt, manufacturer, category, or stock level with server-side pagination.

### 3. Expiry Date Management & Loss Prevention
- **Dynamic Calculation**: Batches categorized dynamically relative to `date.today()`:
  - 🔴 **Expired Stock**: Marked in red; strictly blocked from counter sales.
  - 🟡 **Expiring &le; 30 Days**: Urgent clearance warning with remaining day counter.
  - 🔵 **Expiring &le; 90 Days**: Advance replenishment warning.
- **Valuation at Risk**: Calculates total investment cost and retail loss value per expiry category.
- **Audited Stock Removal**: Dedicated modal to write off expired/damaged units with reason codes (`EXPIRED_REMOVAL`, `DAMAGE_REMOVAL`, `RECALL`, `RETURN`) and audit logs.

### 4. Low Stock Intelligence & Quick Reorder
- Automatically calculates stock deficit `(min_stock - current_stock)` across all active medicines.
- Identifies critical out-of-stock items (0 units left).
- **Direct Reorder Shortcut**: "Order Now" button pre-fills a purchase order with the medicine and recommended restock quantity.

### 5. Multi-Item Inward Purchase Management
- Create procurement invoices from registered suppliers.
- Dynamic multi-row table supporting multiple medicines per purchase order.
- Automatically calculates line subtotal, discount, GST/tax, and grand total.
- **Atomic Database Transactions**: Increases batch stock and records movement history only upon transaction commit.
- **Printable PO Invoice**: Complete goods inward note with supplier GSTIN and signatory authorization blocks.

### 6. Point of Sale (POS) Counter Billing
- **Fast Autocomplete**: Search medicines by brand name, salt, or code (keyboard shortcut: `/`).
- **Stock & Safety Enforcement**:
  - Live available batch quantities displayed.
  - Cannot exceed available batch stock.
  - **Strict Expiry Block**: Expired medicines cannot be added to cart or checked out.
- **Real-Time Financial Arithmetic**: Line items calculate unit price, quantity, discount, and GST rate (0%, 5%, 12%, 18%).
- **Payment Methods**: Cash, UPI / QR, and Card.
- **Cash Tender Calculator**: Quick buttons (Exact, ₹500, ₹1000, ₹2000) with automatic change due calculation.
- **Customer CRM**: Optional customer lookup by phone number or walk-in patient mode.
- **Professional Printable Invoice**: Clean layout with pharmacy DL, GSTIN, doctor/patient info, tax breakup, and print stylesheet for A4 or thermal receipt printers.

### 7. Supplier & Customer Directories
- **Suppliers**: Contact person, phone, email, address, GSTIN, lifetime spend, and supplied medicines catalog.
- **Customers**: Patient phone lookup, total lifetime spend, order history, and instant billing auto-fill.

### 8. Financial Reports & Analytics
- **Distinct Gross Profit**: Accurately calculates `Gross Sales - Discounts - Cost of Goods Sold (COGS) = Estimated Gross Profit` (strictly distinguishing gross margin from net income).
- **Comprehensive Reports**: Daily sales breakdown, sales by medicine, supplier procurement, and inventory valuation.
- **CSV Export**: Single-click CSV export for all reports.
- **System Audit Logs**: Complete trail of logins, sales, purchases, and stock write-offs with IP addresses.

### 9. Security & Role-Based Access Control (RBAC)
- Password hashing with PBKDF2/SHA-256 via Werkzeug.
- Roles: `admin` (full privileges) and `staff` (restricted from deletions and system administration).
- Session security with `HttpOnly` and `SameSite` cookie flags.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | HTML5, Vanilla CSS3 (Custom Medical Design System), JavaScript (ES6+), Font Awesome 6 |
| **Backend** | Python 3.10+ / Flask 3.0+ |
| **Database** | SQLite3 (relational with `PRAGMA foreign_keys = ON` and ACID transactions) |
| **Charts** | Chart.js 4.x (via CDN) |
| **Testing** | Python `unittest` framework |

---

## 📁 Project Structure

```
medicare-pro/
├── app.py                  # Flask application factory, routes wiring, context processors
├── config.py               # Application configuration and pharmacy metadata
├── database.py             # Database connection, helpers, transactions, and audit logger
├── schema.sql              # Relational SQLite schema (11 tables with indices)
├── seed.py                 # Fictional demo dataset generator with --reset flag
├── requirements.txt        # Python package dependencies
├── README.md               # Complete documentation and presentation guide
│
├── routes/                 # Modular Flask Blueprints
│   ├── __init__.py
│   ├── auth.py             # Login, logout, profile, and RBAC decorators
│   ├── dashboard.py        # Dashboard metrics and aggregation queries
│   ├── medicines.py        # Medicine catalog and batch CRUD
│   ├── expiry.py           # Expiry intelligence, tabs, and stock write-off
│   ├── low_stock.py        # Low-stock detection and reorder shortcuts
│   ├── suppliers.py        # Supplier management and purchase records
│   ├── purchases.py        # Multi-item purchase orders and goods inward
│   ├── billing.py          # POS counter checkout and invoice generator
│   ├── customers.py        # Customer directory and purchase histories
│   ├── reports.py          # Financial analytics, valuation, and CSV export
│   └── api.py              # REST API for autocomplete and Chart.js feeds
│
├── templates/              # Jinja2 HTML Templates
│   ├── base.html           # Master layout with responsive sidebar and topbar
│   ├── auth/               # Login and profile templates
│   ├── dashboard/          # Dashboard with KPI cards and charts
│   ├── medicines/          # Catalog index, form, and batch view
│   ├── expiry/             # Expiry tracking and removal modal
│   ├── low_stock/          # Low stock reordering table
│   ├── suppliers/          # Supplier list, form, and view
│   ├── purchases/          # Purchase orders list, multi-item form, invoice
│   ├── billing/            # Interactive POS billing, print invoice, history
│   ├── customers/          # CRM directory, form, profile
│   ├── reports/            # Financial reports and audit logs
│   └── errors/             # Custom 404 and 500 error handlers
│
├── static/
│   ├── css/
│   │   └── style.css       # Healthcare theme, variables, cards, print stylesheet
│   └── js/
│       ├── main.js         # Sidebar toggle, modals, flash alerts
│       ├── pos.js          # Interactive POS cart and cash tender engine
│       └── charts.js       # Chart.js line and doughnut visualization
│
└── tests/                  # Automated Test Suite
    ├── __init__.py
    ├── test_billing.py     # Math, discounts, tax, and checkout flow tests
    ├── test_stock.py       # Atomic deduction, purchase increment, overdraft tests
    ├── test_expiry.py      # Expired medicine sale rejection safety tests
    └── test_auth.py        # Password hashing, sessions, and RBAC permission tests
```

---

## 🚀 Quick Start & Installation

### Step 1: Open Terminal in Project Directory
```powershell
cd C:\Users\aman2\.gemini\antigravity-ide\scratch\medicare-pro
```

### Step 2: Set Up Virtual Environment (Optional if Python is already available)
```powershell
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Seed Demo Database
```powershell
python seed.py --reset
```
*Creates 2 users, 6 suppliers, 26 medicines across categories, 32 realistic batches (safe, near-expiry, and expired), past purchases, and sales.*

### Step 5: Start the Web Application
```powershell
python app.py
```
Open your browser and navigate to: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔑 Demo Login Credentials

| Role | Username | Password | Access Privileges |
|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Full access (Billing, Catalog, Deletions, Purchases, Reports, Audit Logs) |
| **Staff / Pharmacist** | `staff` | `staff123` | Billing, Inventory View, Stock Inward, Customer Lookup |

> *Tip: The login screen contains one-click buttons (`Admin Demo` and `Staff Demo`) to instantly populate credentials during presentations.*

---

## 🧪 Running Automated Tests

Run the full automated test suite using Python's built-in `unittest`:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

**Expected output:**
```
test_inactive_account_blocked ... ok
test_invalid_password_rejected ... ok
test_staff_restricted_from_admin_action ... ok
test_successful_login_and_session ... ok
test_line_total_and_tax_calculation ... ok
test_pos_checkout_flow ... ok
test_api_search_excludes_expired_batches_for_pos ... ok
test_strictly_block_selling_expired_stock ... ok
test_atomic_stock_deduction_on_sale ... ok
test_prevent_insufficient_stock_sale ... ok

----------------------------------------------------------------------
Ran 10 tests in ~3.8s

OK
```

---

## 🎬 5-Minute College Presentation Demo Walkthrough

Use this sequence to deliver an impressive demonstration to professors or evaluators:

1. **Login Page (`/auth/login`)**:
   - Show the clean pharmacy branding and click **"Admin Demo"** to log in instantly.
2. **Dashboard (`/`)**:
   - Point out the 8 real-time KPI statistic cards queried directly from SQLite.
   - Show the 7-day sales revenue trend line chart and category distribution doughnut chart.
   - Highlight the live notification badges in the sidebar for urgent expiries and low stock items.
3. **Point of Sale Billing (`/billing/pos`)**:
   - Press `/` to focus the search bar.
   - Type `"Dolo"` and select `DOL-2025-A1`.
   - Type `"Pan"` and select `Pan 40`.
   - Modify the quantity, adjust discount, and pick GST rate.
   - Enter a customer mobile number (e.g. `9870012345`) to demonstrate auto-lookup of customer `"Ramesh Kumar"`.
   - Select payment mode (Cash), click tender button `₹1000`, show the automatic change calculation, and click **"Complete Sale & Print Bill"**.
4. **Printable Invoice (`/billing/invoice/<id>`)**:
   - Show the generated tax invoice with pharmacy DL, GSTIN, itemized batch details, and click **"Print Invoice"** (preview print layout).
5. **Expiry Safety Enforcement (`/expiry`)**:
   - Show the categorized tabs: Expired, Expiring in 30 Days, Expiring in 90 Days.
   - Demonstrate the safety rule: search for an expired medicine in POS to show that expired stock is blocked from counter sales.
   - Demonstrate the **"Remove Stock"** modal with disposal reason and audit logging.
6. **Low Stock Intelligence (`/low_stock`)**:
   - Show medicines below minimum thresholds and click **"Order Now"** to pre-fill a Purchase Order.
7. **Financial Reports & CSV Export (`/reports`)**:
   - Show the Gross Profit card: explain how `Gross Sales - Discounts - COGS` calculates gross margin.
   - Click **"Export Active Report to CSV"** to demonstrate instant data download.
8. **Role-Based Access Control**:
   - Log out and log in as `staff` (`staff123`).
   - Attempt an administrative deletion to prove that permission restrictions are strictly enforced by the backend.

---

## ⚠️ Known Limitations & Future Roadmap

1. **Barcode Scanner Hardware**: Uses keyboard input emulation; physical barcode scanners operating in USB HID keyboard wedge mode work natively, but direct serial/RS-232 scanners require dedicated driver bridges.
2. **Thermal ESC/POS Raw Printing**: Invoices use modern browser CSS `@media print` suitable for standard A4 and thermal printers. Direct raw ESC/POS byte streaming to USB thermal receipt cutters can be added as a desktop agent.
3. **Single Store / Local Deployment**: Designed for local store or LAN use with SQLite; multi-branch enterprise networks can migrate to PostgreSQL by updating `DATABASE_PATH` in `config.py`.

---

## 📜 License & Academic Usage
This software was developed for academic evaluation as a College Mini Project in Medical Store Management Systems. Built with strict data privacy guidelines using fictional data.
