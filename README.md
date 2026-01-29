# 🧾 Kingfisher ERP

A **developer-first, accounting-correct ERP system** built with **Python and Django**, designed to be **easy to deploy**, **easy to understand**, and **easy to extend**.

This project aims to provide a **full-blown ERP foundation** without the complexity, opacity, or vendor lock-in of traditional ERP platforms.

---

## 🔎 Why This Project Exists

Most ERP systems are:

- Expensive to customize
- Hard to deploy
- Opaque in their accounting logic
- Built around proprietary configuration layers

This project takes a different approach:

> **ERP as readable, modifiable application code — not a black box.**

---

## 🎯 Project Goals

- Provide a complete ERP domain model
- Be accounting-correct by design
- Keep the technical barrier low for people with ERP or accounting experience
- Prefer clarity over abstraction
- Enable best-of-breed integrations instead of all-in-one solutions

---

## 🧩 Scope & Feature Areas

### Finance & Accounting
- General Ledger (GL)
- Accounts Receivable (AR)
- Accounts Payable (AP)
- Sub-ledgers and open-item accounting
- Period closing & revaluation
- Multi-currency support
- VAT / tax handling
- Audit trail & document linkage

### Sales & Customers
- Customers & pricing
- Orders, invoices, and credit notes
- Payment allocation & settlement
- Customer balances and aging

### Purchasing & Vendors
- Vendors & purchase orders
- Goods receipt
- Vendor invoices
- Matching & approval flows

### Inventory & Items
- Items, variants, and units
- Stock movements
- Valuation methods
- Warehouse / location support

### Projects & Cost Tracking
- Project accounting
- Cost and revenue allocation
- Budget vs. actual tracking

### Reporting & BI (via integrations)
- Financial statements
- Operational reports
- Exportable datasets
- API-first reporting access

---

## 🛠️ Technology Stack

- **Python**
- **Django**
- **Django Admin** (default UI)

The system is intentionally built on **boring, proven technology** to maximize longevity and approachability.

---

## 🧠 Why Django Admin (On Purpose)

The Django admin is used as the **primary UI by design**, not as a placeholder.

Reasons:

- Zero frontend setup
- Extremely fast to extend
- Excellent CRUD ergonomics
- Familiar to a large developer base
- Encourages understanding of the data model

For an ERP system, **data correctness and visibility matter more than UI polish**.

If your business requires a different UI:
- Build one
- Integrate one
- Replace the admin entirely

The system does not depend on the admin — it merely ships with a powerful default.

---

## 🔌 Best-of-Breed Integrations

This ERP does **not** try to do everything itself.

You will **not** find:
- Built-in BI dashboards
- Custom charting engines
- Heavy reporting UIs

Instead, the system is designed to:
- Expose clean, normalized data
- Offer API-first access
- Work well with existing Django plugins and external BI tools

Use the best tool for the job.

---

## 📦 Deployment Philosophy

- Simple local setup
- Works with standard databases
- No proprietary services required
- Suitable for self-hosting

Deployment should feel like deploying a **normal Django application**, not an ERP installation project.

---

Best regards  
**Kresten Skovsted Buch**
