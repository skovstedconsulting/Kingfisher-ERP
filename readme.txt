Vision

My intention is to build a full-blown ERP system covering all essential business domains you would expect from a modern ERP platform.

The roadmap is intentionally ambitious. Features will be built incrementally, with correctness, transparency, and extensibility prioritized over speed.

Scope & Feature Areas

The system is designed to cover the following areas:

Finance & Accounting

General Ledger (GL)

Accounts Receivable (AR)

Accounts Payable (AP)

Sub-ledgers and open-item accounting

Period closing & revaluation

Multi-currency support

VAT / tax handling

Audit trail & document linkage

Sales & Customers

Customers & pricing

Orders, invoices, and credit notes

Payment allocation & settlement

Customer balances and aging

Purchasing & Vendors

Vendors & purchase orders

Goods receipt

Vendor invoices

Matching & approval flows

Inventory & Items

Items, variants, and units

Stock movements

Valuation methods

Warehouse / location support

Projects & Cost Tracking

Project accounting

Cost and revenue allocation

Budget vs. actual tracking

Reporting & BI

Financial statements

Operational reports

Exportable datasets

API-first reporting access

Technology & Philosophy

This project is built with Python and Django.

The built-in Django admin interface is used as the default UI.
It is intentionally kept as the primary interface so the system remains:

Easy to deploy

Easy to understand

Easy to modify

You are free—and encouraged—to build or integrate a more specialized UI if it better serves your business needs.

Best-of-Breed Integrations

This ERP does not try to do everything itself.

Wherever possible, best-of-breed tools should be integrated instead of reinvented.
That is why you will not find a built-in reporting or BI layer in this system.

Instead, the system is designed to:

Expose clean, well-structured data

Be easy to connect to external reporting tools

Encourage the use of existing Django plugins or external BI platforms

Design Goals

Keep the codebase as simple as possible

Avoid unnecessary abstraction and magic

Make the system approachable for people with an ERP or accounting background

Prefer clarity over cleverness

This is an ERP you are meant to read, understand, and modify—not configure blindly.

Status

This project is under active development and should be considered foundational.

Breaking changes are expected while the accounting core and domain models are being established.

Best regards
Kresten Skovsted Buch