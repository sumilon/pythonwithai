"""
services/calculator.py
Financial calculation logic — zero framework dependencies, fully unit-testable.
"""
import math
from typing import Any


def indian_format(num: float | None) -> str:
    """Format number in Indian numbering system (lakhs, crores)."""
    if num is None:
        return "0.00"
    negative = num < 0
    num = abs(round(num, 2))
    integer, decimal = f"{num:.2f}".split(".")
    if len(integer) > 3:
        last3 = integer[-3:]
        rest  = integer[:-3]
        parts: list[str] = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        integer = ",".join(parts) + "," + last3
    return ("-" if negative else "") + integer + "." + decimal


def _pos(*args: Any) -> None:
    for v in args:
        if v is None or v <= 0:
            raise ValueError(f"Value must be greater than zero (got {v!r})")


def calc_emi(loan: float, rate: float, years: int) -> dict:
    _pos(loan, rate, years)
    r     = rate / 100 / 12
    n     = years * 12
    emi   = loan * r * (1 + r) ** n / ((1 + r) ** n - 1)
    total = emi * n
    return {"emi": round(emi, 2), "principal": round(loan, 2),
            "interest": round(total - loan, 2), "total": round(total, 2)}


def calc_sip(monthly: float, rate: float, years: int) -> dict:
    _pos(monthly, rate, years)
    r      = rate / 100 / 12
    n      = years * 12
    future = monthly * ((1 + r) ** n - 1) / r * (1 + r)
    return {"invested": round(monthly * n, 2),
            "returns": round(future - monthly * n, 2),
            "total": round(future, 2)}


def calc_lumpsum(amount: float, rate: float, years: int) -> dict:
    _pos(amount, rate, years)
    total = amount * (1 + rate / 100) ** years
    return {"invested": round(amount, 2),
            "returns": round(total - amount, 2),
            "total": round(total, 2)}


def calc_fd(principal: float, rate: float, years: int) -> dict:
    _pos(principal, rate, years)
    total = principal * (1 + rate / 100 / 4) ** (4 * years)
    return {"invested": round(principal, 2),
            "returns": round(total - principal, 2),
            "total": round(total, 2)}


def calc_rd(deposit: float, rate: float, years: int) -> dict:
    """
    Recurring Deposit maturity using the closed-form formula instead of a
    month-by-month loop — O(1) instead of O(n), up to 360x faster for 30-year
    inputs and avoids floating-point accumulation error.

    Formula: M = D * [(1+r)^n - 1] / [1 - (1+r)^(-1/3)]
    where r = quarterly_rate, n = number of quarters.
    """
    _pos(deposit, rate, years)
    qr       = (rate / 100) / 4          # quarterly interest rate
    quarters = years * 4
    # Maturity = sum of each monthly deposit compounded for its remaining term
    # Using geometric series closed form:
    maturity = deposit * ((1 + qr) ** quarters - 1) / (1 - (1 + qr) ** (-1 / 3))
    invested = deposit * years * 12
    return {"invested": round(invested, 2),
            "returns": round(maturity - invested, 2),
            "total": round(maturity, 2)}


def calc_swp(principal: float, withdraw: float,
             rate: float, inflation: float, years: int) -> dict:
    _pos(principal, withdraw, rate, years)
    if inflation < 0:
        raise ValueError("Inflation cannot be negative")
    mr  = rate / 100 / 12
    mir = inflation / 100 / 12
    bal, total_out, cur = principal, 0.0, withdraw
    for _ in range(years * 12):
        bal += bal * mr
        if bal <= 0:
            break
        if bal <= cur:
            total_out += bal
            bal = 0.0
            break
        bal -= cur
        total_out += cur
        cur *= (1 + mir)
    return {"investment": round(principal, 2),
            "withdrawal": round(total_out, 2),
            "final_value": round(bal, 2)}


def calc_weight(price_per_kg: float, grams: float) -> dict:
    _pos(price_per_kg, grams)
    return {"price": round((price_per_kg / 1000) * grams, 2)}


def dispatch(calc_type: str, f: dict) -> dict:
    """Route form data to the correct calculator."""
    match calc_type:
        case "emi":
            return calc_emi(float(f["emi_loan"]), float(f["emi_rate"]), int(f["emi_years"]))
        case "sip":
            return calc_sip(float(f["sip_amount"]), float(f["sip_rate"]), int(f["sip_years"]))
        case "lumpsum":
            return calc_lumpsum(float(f["lumpsum_amount"]), float(f["lumpsum_rate"]), int(f["lumpsum_years"]))
        case "fd":
            return calc_fd(float(f["fd_principal"]), float(f["fd_rate"]), int(f["fd_years"]))
        case "rd":
            return calc_rd(float(f["rd_deposit"]), float(f["rd_rate"]), int(f["rd_years"]))
        case "swp":
            return calc_swp(float(f["swp_principal"]), float(f["swp_withdraw"]),
                            float(f["swp_rate"]), float(f["swp_inflation"]), int(f["swp_years"]))
        case "weight":
            return calc_weight(float(f["price_per_kg"]), float(f["weight_grams"]))
        case _:
            raise ValueError(f"Unknown calculator type: {calc_type!r}")
