# Roadmap

This document outlines the intended direction of the Kingfisher ERP project.
It is a guiding document, not a commitment to timelines.

---

## Phase 1 — Accounting Core (Foundation)

Goal: Accounting correctness and auditability.

- [x] Chart of Accounts
- [x] General Ledger posting engine
- [x] Double-entry validation
- [x] Accounts Receivable (open items)
- [x] Accounts Payable (open items)
- [x] VAT / tax model
- [x] Multi-currency foundations
- [x] Period close & revaluation
- [ ] Audit trail & document linkage
- [x] Import job to get ISO currencies and ISO countries
- [x] Import job to get Danish Government Chart of account of 2026
- [x] Import job to get dayly exchange rates
- [ ] Notes and attachments
- [x] Number Series
- [x] Automatic change document status on posting

---

## Phase 2 — Sales & Purchasing

Goal: Operational flows that feed accounting.

- [X] Customers, Customer Groups
- [x] Vendors, Vendor Groups
- [x] Orders, invoices, credit notes
- [x] Payment allocation & settlement
- [x] Purchase orders
- [ ] Goods receipt
- [ ] Pricelist
- [ ] Pricelist nesting
- [x] Convert documents: Offer -> Order -> Invioce
- [ ] Credit note

---

## Phase 3 — Banking

Goal: Handle and reconsile bank accounts.

- [x] Bank accounts, bank transactions
- [ ] Import transactions
- [x] Reconsile bankaccounts

---
## Phase 4 — Inventory

Goal: Stock correctness, not just quantities.

- [x] Items
- [ ] Variants, units
- [ ] Stock movements
- [ ] Valuation methods
- [ ] Warehouse / location support

---

## Phase 5 — Projects & Cost Control

Goal: Project-based accounting.

- [ ] Find a good dango project to implement
- [ ] Project structures
- [ ] Cost and revenue allocation
- [ ] Budget vs actual tracking

---

## Phase 6 — Integrations & APIs

Goal: Ecosystem over monolith.

- [ ] Stable public APIs
- [ ] Import/export tooling
- [ ] Integration examples (BI, banking, payroll)
- [ ] Support for Microsoft Entra Id
- [ ] Support for Import/Export digital documents

---

## Phase 7 — UI & Experience (Optional)

Goal: Alternative UIs beyond Django Admin.

- [ ] API-first UI
- [x] Simple user UI

