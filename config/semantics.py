DATABASE_SEMANTICS = """
DATABASE: TPC-H

TABLE: customer

Purpose:
Stores customer-level information.

Grain:
One row represents one customer.

Columns:
- c_custkey:
  Unique identifier for the customer.

- c_name:
  Customer name.

- c_address:
  Customer address.

- c_nationkey:
  Identifier representing the customer's nation.
  The interpretation of the referenced nation is defined separately
  when inter-table relationships are documented.

- c_phone:
  Customer phone number.

- c_acctbal:
  Customer account balance.

- c_mktsegment:
  Customer market segment classification.

- c_comment:
  Free-text comment associated with the customer.


TABLE: lineitem

Purpose:
Stores line-item-level information associated with orders.

Grain:
One row represents one line item within an order.

Columns:
- l_orderkey:
  Identifier of the order associated with the line item.

- l_partkey:
  Identifier of the part associated with the line item.

- l_suppkey:
  Identifier of the supplier associated with the line item.

- l_linenumber:
  Line number identifying the line item within an order.

- l_quantity:
  Quantity of the part included in the line item.

- l_extendedprice:
  Extended price of the line item before applying the line-item discount.

- l_discount:
  Discount fraction applied to the line item's extended price.

- l_tax:
  Tax rate associated with the line item.

- l_returnflag:
  Return status/flag associated with the line item.

- l_linestatus:
  Line-item status.

- l_shipdate:
  Date on which the line item was shipped.

- l_commitdate:
  Date by which the line item was committed for shipment.

- l_receiptdate:
  Date on which the line item was received.

- l_shipinstruct:
  Shipping instructions for the line item.

- l_shipmode:
  Shipping mode used for the line item.

- l_comment:
  Free-text comment associated with the line item.


TABLE: nation

Purpose:
Stores nation-level geographic information.

Grain:
One row represents one nation.

Columns:
- n_nationkey:
  Unique identifier for the nation.

- n_name:
  Nation name.

- n_regionkey:
  Identifier representing the region associated with the nation.
  The interpretation of the referenced region is defined separately
  when inter-table relationships are documented.

- n_comment:
  Free-text comment associated with the nation.


TABLE: orders

Purpose:
Stores order-level information.

Grain:
One row represents one order.

Columns:
- o_orderkey:
  Unique identifier for the order.

- o_custkey:
  Identifier representing the customer who placed the order.
  The interpretation of the referenced customer is defined separately
  when inter-table relationships are documented.

- o_orderstatus:
  Current status of the order.

- o_totalprice:
  Total price recorded for the order.

- o_orderdate:
  Date on which the order was placed.

- o_orderpriority:
  Priority assigned to the order.

- o_clerk:
  Clerk associated with the order.

- o_shippriority:
  Shipping priority assigned to the order.

- o_comment:
  Free-text comment associated with the order.


TABLE: part

Purpose:
Stores product/part-level information.

Grain:
One row represents one part.

Columns:
- p_partkey:
  Unique identifier for the part.

- p_name:
  Part name.

- p_mfgr:
  Manufacturer associated with the part.

- p_brand:
  Brand associated with the part.

- p_type:
  Type/category description of the part.

- p_size:
  Size of the part.

- p_container:
  Container or packaging type of the part.

- p_retailprice:
  Retail price of the part.

- p_comment:
  Free-text comment associated with the part.


TABLE: partsupp

Purpose:
Stores information about the supply of parts by suppliers.

Grain:
One row represents a part-supplier supply record.

Columns:
- ps_partkey:
  Identifier representing the supplied part.

- ps_suppkey:
  Identifier representing the supplier providing the part.

- ps_availqty:
  Quantity of the part available from the supplier.

- ps_supplycost:
  Cost at which the supplier supplies the part.

- ps_comment:
  Free-text comment associated with the part-supplier supply record.


TABLE: region

Purpose:
Stores region-level geographic information.

Grain:
One row represents one region.

Columns:
- r_regionkey:
  Unique identifier for the region.

- r_name:
  Region name.

- r_comment:
  Free-text comment associated with the region.


TABLE: supplier

Purpose:
Stores supplier-level information.

Grain:
One row represents one supplier.

Columns:
- s_suppkey:
  Unique identifier for the supplier.

- s_name:
  Supplier name.

- s_address:
  Supplier address.

- s_nationkey:
  Identifier representing the supplier's nation.
  The interpretation of the referenced nation is defined separately
  when inter-table relationships are documented.

- s_phone:
  Supplier phone number.

- s_acctbal:
  Supplier account balance.

- s_comment:
  Free-text comment associated with the supplier.
"""

INTER_TABLE_RELATIONSHIPS = """
INTER-TABLE RELATIONSHIPS

The following relationships describe how records in the database
tables are related. Relationship cardinalities describe the general
data model and should not be interpreted as fixed record counts.


1. CUSTOMER -> NATION

Relationship:
- customer.c_nationkey references nation.n_nationkey.

Cardinality:
- Many customers can belong to one nation.
- This is a many-to-one relationship from customer to nation.


2. SUPPLIER -> NATION

Relationship:
- supplier.s_nationkey references nation.n_nationkey.

Cardinality:
- Many suppliers can belong to one nation.
- This is a many-to-one relationship from supplier to nation.


3. NATION -> REGION

Relationship:
- nation.n_regionkey references region.r_regionkey.

Cardinality:
- Many nations can belong to one region.
- This is a many-to-one relationship from nation to region.


4. CUSTOMER -> ORDERS

Relationship:
- orders.o_custkey references customer.c_custkey.

Cardinality:
- One customer can place many orders.
- Each order belongs to one customer.
- This is a one-to-many relationship from customer to orders.


5. ORDERS -> LINEITEM

Relationship:
- lineitem.l_orderkey references orders.o_orderkey.

Cardinality:
- One order can contain multiple line items.
- Each line item belongs to one order.
- This is a one-to-many relationship from orders to lineitem.


6. LINEITEM -> PART

Relationship:
- lineitem.l_partkey references part.p_partkey.

Cardinality:
- Multiple line items can refer to the same part.
- Each line item refers to one part.
- This is a many-to-one relationship from lineitem to part.


7. LINEITEM -> SUPPLIER

Relationship:
- lineitem.l_suppkey references supplier.s_suppkey.

Cardinality:
- Multiple line items can refer to the same supplier.
- Each line item refers to one supplier.
- This is a many-to-one relationship from lineitem to supplier.


8. PARTSUPP -> PART

Relationship:
- partsupp.ps_partkey references part.p_partkey.

Cardinality:
- One part can have multiple part-supplier records.
- Each part-supplier record refers to one part.
- This is a many-to-one relationship from partsupp to part.


9. PARTSUPP -> SUPPLIER

Relationship:
- partsupp.ps_suppkey references supplier.s_suppkey.

Cardinality:
- One supplier can have multiple part-supplier records.
- Each part-supplier record refers to one supplier.
- This is a many-to-one relationship from partsupp to supplier.


10. PART <-> SUPPLIER THROUGH PARTSUPP

Relationship:
- partsupp represents the association between parts and suppliers.

Cardinality:
- A part can be associated with multiple suppliers.
- A supplier can be associated with multiple parts.
- Therefore, part and supplier have a many-to-many relationship
  through partsupp.

The combination:
    (ps_partkey, ps_suppkey)

identifies a part-supplier association in partsupp.


KEY STRUCTURE

Single-column identifiers:
- customer.c_custkey
- orders.o_orderkey
- part.p_partkey
- supplier.s_suppkey
- nation.n_nationkey
- region.r_regionkey

Composite identifiers:
- lineitem: (l_orderkey, l_linenumber)
- partsupp: (ps_partkey, ps_suppkey)

TABLE GRAIN

- customer: customer-level
- orders: order-level
- lineitem: order-line-level
- part: part-level
- supplier: supplier-level
- partsupp: part-supplier-level
- nation: nation-level
- region: region-level
"""

BUSINESS_KPIS = """
BUSINESS KPI DEFINITIONS

The following KPIs form the controlled business-metric vocabulary
for the current Data Analyst evaluation.

Unless the user explicitly specifies another definition, these
definitions should be used.


1. GROSS REVENUE

Definition:
- Gross revenue represents the total line-item value before applying
  discounts.

Formula:
    SUM(l_extendedprice)

Grain:
- Calculated from line-item values.
- When reported at order level, aggregate line items belonging to
  each order before calculating order-level metrics.


2. DISCOUNT AMOUNT

Definition:
- Discount amount represents the monetary value reduced from gross
  revenue through line-item discounts.

Formula:
    SUM(l_extendedprice * l_discount)

Here l_discount is a fractional discount rate.


3. NET REVENUE

Definition:
- Net revenue represents revenue after applying line-item discounts.

Formula:
    SUM(l_extendedprice * (1 - l_discount))

This is the default revenue measure for business analysis unless
the user explicitly requests gross revenue or another measure.


4. DISCOUNT RATE

Definition:
- Discount rate represents the proportion of gross revenue given
  as discounts.

Formula:
    SUM(l_extendedprice * l_discount)
    /
    SUM(l_extendedprice)

Expressed as a percentage when reported as a rate.

Important:
- Do not calculate the overall discount rate as a simple average
  of individual line-item discount percentages when a revenue-
  weighted discount rate is requested or implied by this KPI
  definition.


5. ORDER COUNT

Definition:
- Order count represents the number of distinct orders.

Formula:
    COUNT(DISTINCT o_orderkey)

When orders are joined with lineitem, use DISTINCT order identifiers
to avoid counting the same order multiple times because an order can
contain multiple line items.


6. AVERAGE ORDER VALUE (AOV)

Definition:
- AOV represents the average net revenue generated per order.

Formula:
    SUM(l_extendedprice * (1 - l_discount))
    /
    COUNT(DISTINCT o_orderkey)

AOV is an order-level metric.

Important:
- Calculate total net revenue and divide by the number of distinct
  orders.
- Do not average line-item revenue values to obtain AOV.
- Do not aggregate orders to customer-level totals before calculating
  AOV.
- When calculating AOV for a group or time period, the denominator
  must represent the distinct orders belonging to that group or
  period.


GENERAL KPI RULES

- Preserve the appropriate data grain for the KPI being calculated.
- Do not change the analytical grain merely because another table
  is available through a join.
- Use DISTINCT order identifiers when calculating order-level
  counts from line-item data.
- When comparing KPI values across periods, preserve the KPI's
  definition consistently across all periods.
- If a user explicitly defines a different metric, follow the user's
  definition rather than silently substituting a default KPI.
"""

FULL_DATABASE_SEMANTICS = f"""
[DATABASE SEMANTICS]
{DATABASE_SEMANTICS}

[INTER-TABLE RELATIONSHIPS]
{INTER_TABLE_RELATIONSHIPS}

[BUSINESS KPI DEFINITIONS]
{BUSINESS_KPIS}
""".strip()

ANALYST_SEMANTICS = """
CORE DATABASE SEMANTICS

TABLE GRAIN
- customer: one row per customer
- orders: one row per order
- lineitem: one row per order line
- part: one row per part
- partsupp: one row per part-supplier association
- supplier: one row per supplier
- nation: one row per nation
- region: one row per region


KEY COLUMNS AND RELATIONSHIPS

- customer.c_custkey identifies a customer.
- orders.o_orderkey identifies an order.
- orders.o_custkey links an order to its customer.
- lineitem.l_orderkey links a line item to its order.
- lineitem.l_partkey links a line item to its part.
- lineitem.l_suppkey links a line item to its supplier.
- part.p_partkey identifies a part.
- supplier.s_suppkey identifies a supplier.
- partsupp.ps_partkey identifies the associated part.
- partsupp.ps_suppkey identifies the associated supplier.
- customer.c_nationkey links a customer to a nation.
- supplier.s_nationkey links a supplier to a nation.
- nation.n_regionkey links a nation to a region.
- partsupp represents the many-to-many association between parts
  and suppliers.

Relationship structure:
- customer -> orders: one-to-many
- orders -> lineitem: one-to-many
- lineitem -> part: many-to-one
- lineitem -> supplier: many-to-one
- customer -> nation: many-to-one
- supplier -> nation: many-to-one
- nation -> region: many-to-one
- part <-> supplier through partsupp: many-to-many


IMPORTANT COLUMN MEANINGS

- l_extendedprice: line-item value before discount.
- l_discount: fractional discount applied to the line item.
- o_orderdate: date on which the order was placed.
- o_totalprice: total price recorded for the order.
- c_mktsegment: customer market segment.
- p_retailprice: retail price of a part.
- ps_supplycost: supplier's supply cost for a part.


CORE KPI GUIDANCE

- Gross revenue = SUM(l_extendedprice)
- Discount amount = SUM(l_extendedprice * l_discount)
- Net revenue = SUM(l_extendedprice * (1 - l_discount))
- Order count = COUNT(DISTINCT o_orderkey)
- AOV = net revenue / distinct order count


IMPORTANT ANALYTICAL RULES

- Preserve the intended grain of the requested metric.
- "Per order" means order-level observations.
- Do not aggregate orders to customer-level totals before computing
  order-level statistics.
- When lineitem is joined with orders, use distinct order identifiers
  for order counts.
- Be careful that joins can change the number of rows available for
  aggregation.
- Use the relationship structure above to construct joins rather than
  assuming relationships from similarly named columns.
"""