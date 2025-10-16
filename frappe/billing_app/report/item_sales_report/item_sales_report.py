import frappe
from frappe.utils import nowdate


def normalize_keys(d):
    """Return a dict with all keys as str (decode bytes keys if needed)."""
    if not d:
        return {}
    return { (k.decode() if isinstance(k, bytes) else k): v for k, v in d.items() }


def execute(filters=None):
    """
    Script report execute() — normalizes filter keys and runs the SQL safely.
    Returns columns, data (same format as standard frappe reports).
    """
    # normalize keys to avoid KeyError: b'item' etc.
    filters = normalize_keys(filters or {})

    params = {
        'from_date': filters.get('from_date') or None,
        'to_date':   filters.get('to_date')   or None,
        'item':      filters.get('item')      or None,
    }

    sql = """
    SELECT
        bi.item,
        bi.item_name,
        bi.category,
        SUM(bi.qty)                   AS total_qty,
        SUM(bi.amount)                AS total_amount,
        SUM(bi.row_tax)               AS total_tax,
        SUM(bi.amount + bi.row_tax)   AS total_line_total,
        COUNT(DISTINCT b.name)        AS invoice_count
    FROM `tabBilling Item` AS bi
    JOIN `tabBilling` AS b
      ON b.name = bi.parent
      AND b.docstatus = 1
    WHERE (%(from_date)s IS NULL OR b.posting_date >= %(from_date)s)
      AND (%(to_date)s   IS NULL OR b.posting_date <= %(to_date)s)
      AND (%(item)s      IS NULL OR bi.item = %(item)s)
    GROUP BY bi.item, bi.item_name, bi.category
    ORDER BY total_amount DESC
    """

    # run query; as_dict=1 gives list of dicts
    rows = frappe.db.sql(sql, params, as_dict=1)

    # Build columns list (adjust labels/types as you prefer)
    columns = [
        {"fieldname":"item", "label":"Item", "fieldtype":"Link", "options":"Item", "width":200},
        {"fieldname":"item_name", "label":"Item Name", "fieldtype":"Data", "width":250},
        {"fieldname":"category", "label":"Category", "fieldtype":"Data", "width":150},
        {"fieldname":"total_qty", "label":"Total Qty", "fieldtype":"Float", "width":100},
        {"fieldname":"total_amount", "label":"Total Amount", "fieldtype":"Currency", "width":150},
        {"fieldname":"total_tax", "label":"Total Tax", "fieldtype":"Currency", "width":120},
        {"fieldname":"total_line_total", "label":"Line Total", "fieldtype":"Currency", "width":150},
        {"fieldname":"invoice_count", "label":"Invoice Count", "fieldtype":"Int", "width":120},
    ]

    # Convert rows (list of dicts) to list-of-lists matching columns ordering
    data = []
    for r in rows:
        data.append([
            r.get("item"),
            r.get("item_name"),
            r.get("category"),
            r.get("total_qty"),
            r.get("total_amount"),
            r.get("total_tax"),
            r.get("total_line_total"),
            r.get("invoice_count"),
        ])

    return columns, data
