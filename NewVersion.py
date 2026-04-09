#!/usr/bin/env python3
"""Tkinter Expense Tracker GUI

Simple GUI for adding, listing, removing, totaling and exporting expenses.
Saves data to `expenses.json` next to this file.
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List

DATA_FILE = os.path.join(os.path.dirname(__file__), "expenses.json")


# Expense: Dataclass representing a single expense record with
# id, date, amount, category, and description.
@dataclass
class Expense:
	id: int
	date: str
	amount: float
	category: str
	description: str = ""


# load_expenses: Reads expenses from the JSON file and returns
# them as a list of Expense objects.
def load_expenses() -> List[Expense]:
	if not os.path.exists(DATA_FILE):
		return []
	with open(DATA_FILE, "r", encoding="utf-8") as f:
		data = json.load(f)
	if isinstance(data, list):
		return [Expense(**item) for item in data]
	items = data.get("expenses", [])
	return [Expense(**item) for item in items]


# save_expenses: Serializes a list of Expense objects and writes them
# into the JSON file, preserving any existing keys.
def save_expenses(items: List[Expense]) -> None:
	data = {}
	if os.path.exists(DATA_FILE):
		with open(DATA_FILE, "r", encoding="utf-8") as f:
			try:
				existing = json.load(f)
			except Exception:
				existing = {}
			if isinstance(existing, dict):
				data = existing
	data["expenses"] = [asdict(i) for i in items]
	with open(DATA_FILE, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2, ensure_ascii=False)


# load_data: Loads the full data file (expenses, general budget, category budgets)
# with safe defaults if the file is missing or malformed.
def load_data() -> dict:
	if not os.path.exists(DATA_FILE):
		return {"expenses": [], "general_budget": None, "category_budgets": {}}
	with open(DATA_FILE, "r", encoding="utf-8") as f:
		try:
			data = json.load(f)
		except Exception:
			return {"expenses": [], "general_budget": None, "category_budgets": {}}
	if isinstance(data, list):
		return {"expenses": data, "general_budget": None, "category_budgets": {}}
	data.setdefault("expenses", [])
	data.setdefault("general_budget", None)
	data.setdefault("category_budgets", {})
	return data


# save_data: Writes the entire data dictionary back to the JSON file.
def save_data(data: dict) -> None:
	with open(DATA_FILE, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2, ensure_ascii=False)


# next_id: Returns the next available integer ID by incrementing
# the current maximum expense ID.
def next_id(items: List[Expense]) -> int:
	return max((i.id for i in items), default=0) + 1


# ExpenseApp: Main application window; manages the expense list,
# budgets, and all UI interactions.
class ExpenseApp(tk.Tk):

	# __init__: Initializes the window, sets up internal state,
	# builds the UI, and loads saved data.
	def __init__(self):
		super().__init__()
		self.title("Expense Tracker")
		self.geometry("800x700")

		self.items: List[Expense] = []
		self.data = {"expenses": [], "general_budget": None, "category_budgets": {}}

		self._build_ui()
		self._load()

	# _build_ui: Constructs all widgets — input fields, action buttons,
	# the expense table, budget controls, and the status bar.
	def _build_ui(self) -> None:
		frm = ttk.Frame(self)
		frm.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

		left = ttk.Frame(frm)
		left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

		ttk.Label(left, text="Amount:").grid(row=0, column=0, sticky=tk.W)
		self.amount_var = tk.StringVar()
		ttk.Entry(left, textvariable=self.amount_var).grid(row=0, column=1)

		ttk.Label(left, text="Category:").grid(row=1, column=0, sticky=tk.W)
		self.category_var = tk.StringVar(value="misc")
		ttk.Entry(left, textvariable=self.category_var).grid(row=1, column=1)

		ttk.Label(left, text="Date (YYYY-MM-DD):").grid(row=2, column=0, sticky=tk.W)
		self.date_var = tk.StringVar(value=datetime.now().date().isoformat())
		ttk.Entry(left, textvariable=self.date_var).grid(row=2, column=1)

		ttk.Label(left, text="Description:").grid(row=3, column=0, sticky=tk.W)
		self.desc_var = tk.StringVar()
		ttk.Entry(left, textvariable=self.desc_var).grid(row=3, column=1)

		ttk.Button(left, text="Add", command=self.add_expense).grid(row=4, column=0, columnspan=2, pady=(8, 0))
		ttk.Button(left, text="Edit Selected", command=self.edit_selected).grid(row=5, column=0, columnspan=2, pady=(8, 0))
		ttk.Button(left, text="Remove Selected", command=self.remove_selected).grid(row=6, column=0, columnspan=2, pady=(8, 0))
		ttk.Button(left, text="Total", command=self.show_total).grid(row=7, column=0, columnspan=2, pady=(8, 0))
		ttk.Button(left, text="Export CSV", command=self.export_csv).grid(row=8, column=0, columnspan=2, pady=(8, 0))
		ttk.Button(left, text="Clear All", command=self.clear_all).grid(row=9, column=0, columnspan=2, pady=(8, 0))

		# Budget controls
		ttk.Separator(left, orient=tk.HORIZONTAL).grid(row=10, column=0, columnspan=2, sticky="ew", pady=(8, 8))
		ttk.Label(left, text="General Monthly Budget:").grid(row=11, column=0, sticky=tk.W)
		self.general_budget_var = tk.StringVar()
		ttk.Entry(left, textvariable=self.general_budget_var).grid(row=11, column=1)
		ttk.Button(left, text="Set General Budget", command=self.set_general_budget).grid(row=12, column=0, columnspan=2, pady=(4, 0))

		ttk.Label(left, text="Category: (for category budget)").grid(row=13, column=0, sticky=tk.W)
		self.cat_budget_category_var = tk.StringVar()
		ttk.Entry(left, textvariable=self.cat_budget_category_var).grid(row=13, column=1)
		ttk.Label(left, text="Amount:").grid(row=14, column=0, sticky=tk.W)
		self.cat_budget_amount_var = tk.StringVar()
		ttk.Entry(left, textvariable=self.cat_budget_amount_var).grid(row=14, column=1)
		ttk.Button(left, text="Set Category Budget", command=self.set_category_budget).grid(row=15, column=0, columnspan=2, pady=(4, 0))

		right = ttk.Frame(frm)
		right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

		cols = ("id", "date", "amount", "category", "description")
		self.tree = ttk.Treeview(right, columns=cols, show="headings")
		for c in cols:
			label = "ID" if c == "id" else c.title()
			self.tree.heading(c, text=label)
			if c == "description":
				self.tree.column(c, width=300)
			else:
				self.tree.column(c, width=80)
		self.tree.pack(fill=tk.BOTH, expand=True)

		self.status = ttk.Label(self, text="")
		self.status.pack(fill=tk.X)

	# _load: Reads saved data from disk, populates the expense list,
	# and pre-fills the budget field for the current month.
	def _load(self) -> None:
		data = load_data()
		self.data = data
		self.items = [Expense(**e) for e in data.get("expenses", [])]
		self.refresh_tree()

		gb = self.data.get("general_budget")
		if gb and gb.get("month") == datetime.now().date().isoformat()[:7]:
			self.general_budget_var.set(str(gb.get("amount")))

	# refresh_tree: Clears and repopulates the expense table from the current
	# list; updates the status bar summary with expense count and budget info.
	def refresh_tree(self) -> None:
		for r in self.tree.get_children():
			self.tree.delete(r)
		for i in self.items:
			self.tree.insert("", tk.END, values=(i.id, i.date, f"{i.amount:.2f}", i.category, i.description))
		msgs = [f"{len(self.items)} expenses"]
		gb = self.data.get("general_budget")
		if gb:
			msgs.append(f"General budget: {gb.get('amount')} for {gb.get('month')}")
		cb = self.data.get("category_budgets", {})
		if cb:
			msgs.append(f"Category budgets: {len(cb)}")
		self.status.config(text=" | ".join(msgs))

	# add_expense: Validates inputs and either adds a new expense or saves edits
	# to an existing one, then persists to disk, refreshes the table, and runs
	# budget threshold checks via notify_if_threshold.
	def add_expense(self) -> None:
		amt_s = self.amount_var.get().strip()
		try:
			amt = float(amt_s)
		except Exception:
			messagebox.showerror("Invalid amount", "Please enter a numeric amount.")
			return
		date = self.date_var.get().strip() or datetime.now().date().isoformat()
		cat = self.category_var.get().strip() or "misc"
		desc = self.desc_var.get().strip()
		if hasattr(self, '_saved_id_for_edit') and getattr(self, '_saved_id_for_edit') is not None:
			rid = self._saved_id_for_edit
			for idx, it in enumerate(self.items):
				if it.id == rid:
					self.items[idx] = Expense(id=rid, date=date, amount=amt, category=cat, description=desc)
					break
			self._saved_id_for_edit = None
		else:
			exp = Expense(id=next_id(self.items), date=date, amount=amt, category=cat, description=desc)
			self.items.append(exp)
		self.data["expenses"] = [asdict(i) for i in self.items]
		save_data(self.data)
		self.refresh_tree()
		self.amount_var.set("")
		self.desc_var.set("")
		self.notify_if_threshold(exp)

	# notify_if_threshold: Runs two independent budget checks after each expense is added.
	# First, checks if the running total for the expense's category has reached 90% or more
	# of the set category budget for that month and shows a warning if so.
	# Second, checks if the total of all expenses for the month has reached 90% or more
	# of the general monthly budget and shows a separate warning if so.
	# Either or both alerts may fire depending on which budgets are configured.
	def notify_if_threshold(self, expense: Expense) -> None:
		month = expense.date[:7]
		cat = expense.category

		# Check category budget
		total_cat = sum(e.amount for e in self.items if e.category == cat and e.date[:7] == month)
		cb = self.data.get("category_budgets", {})
		cat_budget = None
		if isinstance(cb.get(cat), dict) and cb.get(cat).get("month") == month:
			cat_budget = float(cb.get(cat).get("amount"))
		if cat_budget is not None and total_cat >= 0.9 * cat_budget:
			messagebox.showwarning("Budget Alert", f"You have reached {total_cat:.2f} which is >= 90% of your {cat} budget ({cat_budget:.2f}) for {month}.")

		# Check general monthly budget
		gb = self.data.get("general_budget")
		if gb and gb.get("month") == month:
			gen_budget = float(gb.get("amount"))
			total_month = sum(e.amount for e in self.items if e.date[:7] == month)
			if total_month >= 0.9 * gen_budget:
				messagebox.showwarning("Monthly Budget Alert", f"You have reached {total_month:.2f} which is >= 90% of your general monthly budget ({gen_budget:.2f}) for {month}.")

	# remove_selected: Deletes the selected expense from the list,
	# persists the change to disk, and refreshes the table.
	def remove_selected(self) -> None:
		sel = self.tree.selection()
		if not sel:
			messagebox.showinfo("Remove", "Select a row to remove.")
			return
		vals = self.tree.item(sel[0], "values")
		try:
			rid = int(vals[0])
		except Exception:
			messagebox.showerror("Error", "Unable to determine id of selected row.")
			return
		self.items = [i for i in self.items if i.id != rid]
		for idx, item in enumerate(self.items, start=1):
			item.id = idx
		self.data["expenses"] = [asdict(i) for i in self.items]
		save_data(self.data)
		self.refresh_tree()

	# edit_selected: Populates the input fields with the selected expense's values
	# so the user can modify and re-save it via the Add button.
	def edit_selected(self) -> None:
		sel = self.tree.selection()
		if not sel:
			messagebox.showinfo("Edit", "Select a row to edit.")
			return
		vals = self.tree.item(sel[0], "values")
		try:
			rid = int(vals[0])
		except Exception:
			messagebox.showerror("Error", "Unable to determine id of selected row.")
			return
		exp = next((i for i in self.items if i.id == rid), None)
		if not exp:
			messagebox.showerror("Edit", "Expense not found.")
			return
		self.amount_var.set(str(exp.amount))
		self.category_var.set(exp.category)
		self.date_var.set(exp.date)
		self.desc_var.set(exp.description)
		self._saved_id_for_edit = rid

	# clear_all: After confirmation, wipes all expenses and budgets
	# from both memory and disk, then refreshes the table.
	def clear_all(self) -> None:
		if not messagebox.askyesno("Clear All", "Are you sure you want to delete all expenses and budgets?"):
			return
		self.items = []
		self.data = {"expenses": [], "general_budget": None, "category_budgets": {}}
		save_data(self.data)
		self.refresh_tree()

	# set_general_budget: Saves a monthly general budget amount entered by the user,
	# tagged to the current month, and persists it to disk.
	def set_general_budget(self) -> None:
		amt_s = self.general_budget_var.get().strip()
		if not amt_s:
			messagebox.showinfo("General Budget", "Enter an amount.")
			return
		try:
			amt = float(amt_s)
		except Exception:
			messagebox.showerror("Invalid", "Enter numeric amount for general budget.")
			return
		month = datetime.now().date().isoformat()[:7]
		self.data["general_budget"] = {"amount": amt, "month": month}
		save_data(self.data)
		self.refresh_tree()
		messagebox.showinfo("General Budget", f"Set general budget to {amt:.2f} for {month}")

	# set_category_budget: Saves a per-category monthly budget, validating that the
	# sum of all category budgets does not exceed the general monthly budget if one is set.
	def set_category_budget(self) -> None:
		cat = self.cat_budget_category_var.get().strip()
		amt_s = self.cat_budget_amount_var.get().strip()
		if not cat or not amt_s:
			messagebox.showinfo("Category Budget", "Enter category and amount.")
			return
		try:
			amt = float(amt_s)
		except Exception:
			messagebox.showerror("Invalid", "Enter numeric amount for category budget.")
			return
		month = datetime.now().date().isoformat()[:7]
		gb = self.data.get("general_budget")
		if gb and gb.get("month") == month:
			sum_cat = sum(float(v.get("amount")) for k, v in self.data.get("category_budgets", {}).items() if v.get("month") == month and k != cat)
			if sum_cat + amt > float(gb.get("amount")):
				messagebox.showerror("Limit", "Category budgets exceed general monthly budget.")
				return
		self.data.setdefault("category_budgets", {})
		self.data["category_budgets"][cat] = {"amount": amt, "month": month}
		save_data(self.data)
		self.refresh_tree()
		messagebox.showinfo("Category Budget", f"Set budget for {cat}: {amt:.2f} for {month}")

	# show_total: Displays the sum of all current expenses in a dialog.
	def show_total(self) -> None:
		total = sum(i.amount for i in self.items)
		messagebox.showinfo("Total", f"Total expenses: {total:.2f}")

	# export_csv: Prompts for a file path and exports all expenses to a CSV file
	# with columns: id, date, amount, category, description.
	def export_csv(self) -> None:
		if not self.items:
			messagebox.showinfo("Export", "No expenses to export.")
			return
		path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile="expenses_export.csv")
		if not path:
			return
		with open(path, "w", newline="", encoding="utf-8") as f:
			writer = csv.writer(f)
			writer.writerow(["id", "date", "amount", "category", "description"])
			for i in self.items:
				writer.writerow([i.id, i.date, f"{i.amount:.2f}", i.category, i.description])
		messagebox.showinfo("Export", f"Exported {len(self.items)} rows to {path}")


# main: Entry point — creates and runs the ExpenseApp window.
def main() -> None:
	app = ExpenseApp()
	app.mainloop()


if __name__ == "__main__":
	main()
