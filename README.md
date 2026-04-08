# StockFlow Inventory Management

StockFlow is a backend system designed for B2B SaaS inventory management. This project addresses critical reliability issues in inventory tracking, implements a scalable multi-warehouse database architecture, and provides automated low-stock alerting based on actual sales velocity.

## Core Features
- **Reliable Product Entry**: Fixed transaction atomicity issues and added strict SKU validation to prevent data corruption.
- **Advanced DB Schema**: Built for PostgreSQL with support for Companies, Warehouses, Suppliers, and Product Bundles (BOM).
- **Proactive Alerts**: Logic-based low-stock endpoint that factors in 30-day sales velocity to predict stockout dates.
- **Hardened API**: Full implementation of pagination, 404 handling, and input sanitization.

## Setup & Testing
1. **Install Dependencies**: `pip install flask flask-sqlalchemy pytest`
2. **Database Initialization**: SQL DDL is provided in `schema.sql`. The app uses SQLite by default for easy local testing.
3. **Run Tests**: `set PYTHONPATH=. && pytest tests/test_stockflow.py`
4. **Start API**: `python app.py`

## Project Structure
- `app.py`: API endpoints and core business logic.
- `models.py`: Database models and relationships.
- `schema.sql`: Production-ready PostgreSQL DDL.
- `tests/`: Pytest suite for business logic verification.
- `submission.md`: Technical analysis and design decisions.
