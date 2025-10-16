frappe.ui.form.on('Billing', {
  refresh(frm) {
    frm.trigger('compute_totals_ui');
  },
  is_paid: (frm) => frm.trigger('compute_totals_ui'),
  due_date: (frm) => frm.trigger('compute_totals_ui'),

  compute_totals_ui(frm) {
    let subtotal = 0, tax_total = 0;

    (frm.doc.items || []).forEach(r => {
      const amount = (r.qty || 0) * (r.rate || 0);
      const row_tax = amount * ((r.tax_percent || 0) / 100.0);
      r.amount = amount;
      r.row_tax = row_tax;
      subtotal += amount;
      tax_total += row_tax;
    });

    // Set immediate UI values (server will overwrite on save)
    frm.set_value('subtotal', subtotal);
    frm.set_value('tax_amount', tax_total);

    const set_finals = (has_prev) => {
      const discount = has_prev ? (subtotal * 0.05) : 0;
      const grand = Math.max(0, subtotal - discount + tax_total);
      frm.set_value('discount_amount', discount);
      frm.set_value('grand_total', grand);

      // Status preview (not authoritative)
      if (frm.doc.docstatus === 0) {
        frm.set_value('status', 'Draft');
      } else if (frm.doc.is_paid) {
        frm.set_value('status', 'Paid');
      } else {
        const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
        const due = frm.doc.due_date ? frappe.datetime.str_to_obj(frm.doc.due_date) : null;
        frm.set_value('status', (due && due < today) ? 'Overdue' : 'Unpaid');
      }

      frm.refresh_field('items');
    };

    if (frm.doc.customer) {
      // Ask server if there is a previous submitted Billing for this customer (excluding current)
      frappe.call({
        method: "frappe.client.get_count",
        args: {
          doctype: "Billing",
          filters: { customer: frm.doc.customer, docstatus: 1, name: ["!=", frm.doc.name || ""] }
        },
        callback: (r) => set_finals((r && r.message > 0))
      });
    } else {
      set_finals(false);
    }
  }
});

frappe.ui.form.on('Billing Item', {
  item: async function(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    if (!row.item) return;
    const d = await frappe.db.get_value('Item', row.item, ['item_name','category','rate']);
    if (d && d.message) {
      row.item_name = d.message.item_name;
      row.category  = d.message.category;
      if (!row.rate) row.rate = d.message.rate;
      frm.refresh_field('items');
      frm.trigger('compute_totals_ui');
    }
  },
  qty: (frm) => frm.trigger('compute_totals_ui'),
  rate: (frm) => frm.trigger('compute_totals_ui'),
  tax_percent: (frm) => frm.trigger('compute_totals_ui'),
});
