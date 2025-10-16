import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, getdate, flt
from frappe import _


def send_billing_email(doc, method=None):
    """Email the customer when a Billing document is submitted."""
    # 1) get recipient
    if not doc.customer:
        return

    to_email = frappe.db.get_value("Customer", doc.customer, "email")
    if not to_email:
        frappe.logger().info(f"[Billing Email] No email for customer {doc.customer}; skipping send.")
        return

    # 2) build HTML body
    rows = []
    for it in doc.items:
        rows.append(f"""
        <tr>
          <td>{(it.item_name or it.item) or ""}</td>
          <td style="text-align:right">{flt(it.qty, 2)}</td>
          <td style="text-align:right">{flt(it.rate, 2):.2f}</td>
          <td style="text-align:right">{flt(it.tax_percent, 2):.2f}%</td>
          <td style="text-align:right">{flt(it.amount, 2):.2f}</td>
          <td style="text-align:right">{flt(it.row_tax, 2):.2f}</td>
        </tr>
        """)

    table_html = "".join(rows)
    subject = _(f"Invoice {doc.name} - {doc.status}")

    body = f"""
    <h2>Invoice {( doc.name )}</h2>
	<p><b>Customer:</b> {( doc.customer )}<br/>
	<b>Posting Date:</b> {( doc.posting_date )}<br/>
	<b>Due Date:</b> {( doc.due_date )}<br/>
	<b>Status:</b> {( doc.status )}</p>

	<table class="table table-bordered">
	<thead>
		<tr>
		<th>Item</th>
		<th style="text-align:right">Qty</th>
		<th style="text-align:right">Rate</th>
		<th style="text-align:right">Tax %</th>
		<th style="text-align:right">Amount</th>
		<th style="text-align:right">Row Tax</th>
		</tr>
	</thead>
	<tbody>
		{table_html}
	</tbody>
	</table>

	<p style="text-align:right">
	<b>Subtotal:</b> {( doc.subtotal )}<br/>
	<b>Discount:</b> {( doc.discount_amount )}<br/>
	<b>Tax:</b> {( doc.tax_amount )}<br/>
	<b>Grand Total:</b> {( doc.grand_total ) }<br/>
	</p>
    """

    # 4) send (queued by default)
    try:
        frappe.sendmail(
            recipients=[to_email],
            subject=subject,
            message=body,
            reference_doctype="Billing",
            reference_name=doc.name,
            delayed=True,     # queue via Email Queue (recommended)
        )
        frappe.logger().info(f"[Billing Email] Queued email for {doc.name} to {to_email}")
    except Exception:
        # Don't block submission on email failure
        frappe.logger().error(f"[Billing Email] Send failed for {doc.name}", exc_info=True)

DISCOUNT_PERCENT_IF_PREVIOUS_PURCHASE = 5.0

def _has_previous_purchase(customer: str, current_name: str | None = None) -> bool:
    filters = {"customer": customer, "docstatus": 1}
    if current_name:
        filters["name"] = ["!=", current_name]
    return bool(frappe.db.exists("Billing", filters))

def _compute_row(item):
    qty = flt(item.qty); rate = flt(item.rate); tax_pc = flt(item.tax_percent)
    amount = qty * rate
    row_tax = amount * tax_pc / 100.0
    item.amount = amount
    item.row_tax = row_tax
    return amount, row_tax

def _apply_totals_and_status(doc):
    if not doc.items:
        frappe.throw("Add at least one Item.")
    if not doc.due_date and doc.docstatus:  # on submit
        frappe.throw("Due Date is required.")

    subtotal = tax_total = 0.0
    for it in doc.items:
        a, t = _compute_row(it)
        subtotal += a
        tax_total += t

    discount = 0.0
    if doc.customer and _has_previous_purchase(doc.customer, doc.name if doc.name else None):
        discount = subtotal * DISCOUNT_PERCENT_IF_PREVIOUS_PURCHASE / 100.0

    doc.subtotal = subtotal
    doc.tax_amount = tax_total
    doc.discount_amount = discount
    doc.grand_total = max(0.0, subtotal - discount + tax_total)

    if doc.docstatus == 0:
        doc.status = "Draft"
    elif doc.is_paid:
        doc.status = "Paid"
    else:
        today = getdate(nowdate())
        due = getdate(doc.due_date) if doc.due_date else None
        doc.status = "Overdue" if (due and due < today) else "Unpaid"

class Billing(Document):
    def validate(self):
        _apply_totals_and_status(self)

    def before_submit(self):
        _apply_totals_and_status(self)

    def on_submit(self):
        send_billing_email(self)
