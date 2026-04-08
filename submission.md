# StockFlow Case Study Submission

## Part 1: Code Review & Debugging Analysis

### Identified Bugs & Production Impacts
1.  **Multiple Transaction Commits**:
    - **Issue**: `db.session.commit()` was called twice (once for Product, once for Inventory).
    - **Impact**: Inconsistent state. If the second commit fails (e.g., db timeout, validation error), the product exists in the DB but has no inventory record. This breaks downstream logic like low-stock alerts.
2.  **Lack of SKU Uniqueness Enforcement**:
    - **Issue**: No check for existing SKUs before insertion.
    - **Impact**: Data corruption. Multiple products can share the same SKU, making inventory tracking across warehouses ambiguous and causing order fulfillment errors.
3.  **Unsafe Dictionary Access**:
    - **Issue**: Direct use of `data['key']` without validation.
    - **Impact**: 500 Internal Server Errors (KeyError) whenever a client sends a payload missing any field, degrading API reliability and user experience.
4.  **Floating Point Precision (Price)**:
    - **Issue**: `price=data['price']` doesn't handle decimal precision.
    - **Impact**: Precision errors in financial calculations (e.g., total inventory value). Over time, these small errors accumulate, leading to accounting discrepancies.
5.  **Lack of Error Handling**:
    - **Issue**: No try/except/rollback blocks.
    - **Impact**: Database locks might persist if a transaction fails mid-way, and errors are not gracefully returned as structured JSON to the client.

---

## Part 2: Database Design

The PostgreSQL schema is designed for multi-tenancy and high reliability.

- **Full SQL DDL**: Refer to [schema.sql](file:///c:/Assignment_DH/vocalflow-main/schema.sql)
- **Text-based ERD**: Refer to [erd.txt](file:///c:/Assignment_DH/vocalflow-main/erd.txt)

---

## Part 3: Low-Stock API & Hardening

### Implementation Details
- **Endpoint**: `GET /api/companies/{id}/alerts/low-stock`
- **Logic**: Calculates `avg_daily_sales` based on the last 30 days of sales data.
- **Formula**: `days_until_stockout = current_stock / (total_sold_last_30 / 30)`.
- **Filtering**: Automatically excludes products with no sales activity in the last 30 days to focus on high-velocity items.

### Hardening Measures
- **Validation**: 404 response for invalid Company IDs.
- **Performance**: Pagination (`page`, `limit`) prevents large responses from timing out.
- **Filtering**: Optional `warehouse_id` filter for localized stock management.

---

## Part 4: Testing & Assumptions

### Testing Results
Pytest cases verified:
- `test_create_product_happy_path`: SUCCESS
- `test_create_product_duplicate_sku`: SUCCESS
- `test_low_stock_calculation`: SUCCESS (Verified 2.5 days stockout logic)

### Assumptions Made
1.  **Sales Calculation**: Assumed a rolling 30-day window for "recent activity."
2.  **Average Daily Sales**: Assumed that if a product has NO sales in 30 days, it shouldn't trigger a low-stock alert even if stock is low (per requirements: "Only alert for products with recent sales activity").
3.  **Inventory for Bundles**: Assumed bundles are tracked as separate SKUs, but their membership is documented in the `product_bundles` table for future BOM logic.

### 5 Questions for the Product Team
1.  **Bundle Inventory**: Should bundle inventory be calculated dynamically from components, or is a bundle "built" and stocked as its own item?
2.  **Multi-Tenant Isolation**: Do we need strict tenant-level separation at the DB layer (e.g., separate schemas) or is application-level `company_id` filtering sufficient?
3.  **Sales Window Config**: Should the 30-day "activity window" be global or configurable per product category?
4.  **Alert Thresholds**: Are thresholds static per product, or should they be dynamic based on seasonal trends?
5.  **Wholesale/Retail**: Do we need to distinguish between different price types (Wholesale vs. MSRP) in the product model?

### Scalability Choices
1.  **SKU Indexing**: A unique B-Tree index on `sku` ensures $O(\log n)$ lookup time even with millions of products.
2.  **Foreign Key Indices**: All FKs (`company_id`, `product_id`, `warehouse_id`) are indexed to optimize JOIN performance for reporting queries.
3.  **Composite Index on Sales**: `(product_id, warehouse_id, sold_at)` allows extremely fast average daily sales calculations over a 30-day range.
4.  **Pagination**: Mandating pagination at the API layer prevents memory exhaustion at scale.
