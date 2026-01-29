# Roadmap

This document outlines the intended direction of the Kingfisher ERP project.
It is a guiding document, not a commitment to timelines.

---

## Phase 1 — Accounting Core (Foundation)

Goal: Accounting correctness and auditability.

- [x] Chart of Accounts
- [ ] General Ledger posting engine
- [x] Double-entry validation
- [ ] Accounts Receivable (open items)
- [ ] Accounts Payable (open items)
- [ ] VAT / tax model
- [ ] Multi-currency foundations
- [ ] Period close & revaluation
- [ ] Audit trail & document linkage
- [x] Import job to get ISO currencies and ISO countries
- [x] Import job to get Danish Government Chart of account of 2026
- [ ] Import job to get dayly exchange rates
- [ ] Notes and attachments

---

## Phase 2 — Sales & Purchasing

Goal: Operational flows that feed accounting.

- [ ] Customers & vendors
- [ ] Orders, invoices, credit notes
- [ ] Payment allocation & settlement
- [ ] Purchase orders
- [ ] Goods receipt
- [ ] Invoice matching

---

## Phase 3 — Banking

Goal: Handle and reconsile bank accounts.

- [ ] Bank accounts, bank transactions
- [ ] Import transactions
- [ ] Reconsile bankaccounts

---
## Phase 4 — Inventory

Goal: Stock correctness, not just quantities.

- [ ] Items, variants, units
- [ ] Stock movements
- [ ] Valuation methods
- [ ] Warehouse / location support

---

## Phase 5 — Projects & Cost Control

Goal: Project-based accounting.

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
- [ ] Reference frontend (optional)
