# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Item(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category: DF.Literal["Grocery", "Vegetable&Fruits", "Electronics", "Furniture", "Clothing", "Food & Beverages", "Health & Beauty", "Stationery & Office Supplies", "Automotive", "Home Appliances", "Books & Media", "Sports & Fitness", "Toys & Games", "IT & Software", "Services", "Others"]
		image: DF.AttachImage | None
		item_name: DF.Data
		rate: DF.Currency
	# end: auto-generated types

	pass
