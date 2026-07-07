"""
calculator_tools.py - Calculator endpoints, termasuk kalkulator jaringan (subnet/CIDR)
untuk kebutuhan network integration & sysadmin.
"""
import ipaddress
from datetime import datetime

from flask import Blueprint, request

from utils import error_response, ok_response

calc_bp = Blueprint("calculator_tools", __name__, url_prefix="/api/calc")


def _body():
    return request.get_json(silent=True) or {}


@calc_bp.route("/subnet", methods=["POST"])
def subnet():
    """Kalkulator subnet/CIDR. Body: {cidr} contoh '192.168.1.0/24'."""
    body = _body()
    cidr = body.get("cidr", "")
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError as e:
        return error_response(f"CIDR tidak valid: {e}")

    hosts = list(net.hosts())
    return ok_response({
        "network": str(net.network_address),
        "broadcast": str(net.broadcast_address) if net.version == 4 else None,
        "netmask": str(net.netmask),
        "wildcard_mask": str(net.hostmask),
        "prefix_length": net.prefixlen,
        "total_addresses": net.num_addresses,
        "usable_hosts": len(hosts) if net.version == 4 else net.num_addresses - 2,
        "first_usable": str(hosts[0]) if hosts else None,
        "last_usable": str(hosts[-1]) if hosts else None,
        "is_private": net.is_private,
        "version": net.version,
    })


@calc_bp.route("/ip-in-network", methods=["POST"])
def ip_in_network():
    """Cek apakah IP termasuk dalam suatu network. Body: {ip, cidr}."""
    body = _body()
    try:
        ip = ipaddress.ip_address(body.get("ip", ""))
        net = ipaddress.ip_network(body.get("cidr", ""), strict=False)
        return ok_response({"ip": str(ip), "network": str(net), "is_member": ip in net})
    except ValueError as e:
        return error_response(str(e))


@calc_bp.route("/subnet-split", methods=["POST"])
def subnet_split():
    """Pecah network jadi beberapa subnet lebih kecil. Body: {cidr, new_prefix}."""
    body = _body()
    try:
        net = ipaddress.ip_network(body.get("cidr", ""), strict=False)
        new_prefix = int(body.get("new_prefix"))
        subnets = list(net.subnets(new_prefix=new_prefix))
        return ok_response({
            "count": len(subnets),
            "subnets": [str(s) for s in subnets[:1000]],  # batasi output
            "truncated": len(subnets) > 1000,
        })
    except (ValueError, TypeError) as e:
        return error_response(str(e))


@calc_bp.route("/base-convert", methods=["POST"])
def base_convert():
    """Convert angka antar basis. Body: {value, from_base, to_base} basis: 2/8/10/16."""
    body = _body()
    value = str(body.get("value", ""))
    from_base = int(body.get("from_base", 10))
    to_base = int(body.get("to_base", 16))

    try:
        n = int(value, from_base)
    except ValueError:
        return error_response(f"'{value}' bukan angka valid pada basis {from_base}.")

    mapping = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if n == 0:
        result = "0"
    else:
        digits = []
        neg = n < 0
        n = abs(n)
        while n:
            digits.append(mapping[n % to_base])
            n //= to_base
        result = ("-" if neg else "") + "".join(reversed(digits))

    return ok_response({
        "decimal": int(value, from_base),
        "binary": bin(int(value, from_base))[2:],
        "octal": oct(int(value, from_base))[2:],
        "hex": hex(int(value, from_base))[2:].upper(),
        "result_base_" + str(to_base): result,
    })


@calc_bp.route("/percentage", methods=["POST"])
def percentage():
    """Kalkulator persen. Body: {operation, a, b}.
    operation: 'a_percent_of_b' | 'a_is_what_percent_of_b' | 'percent_change'
    """
    body = _body()
    op = body.get("operation")
    a = float(body.get("a", 0))
    b = float(body.get("b", 0))

    if op == "a_percent_of_b":
        result = (a / 100) * b
    elif op == "a_is_what_percent_of_b":
        result = (a / b) * 100 if b else None
    elif op == "percent_change":
        result = ((b - a) / a) * 100 if a else None
    else:
        return error_response("operation harus salah satu: a_percent_of_b, a_is_what_percent_of_b, percent_change")

    return ok_response({"result": result})


@calc_bp.route("/date-diff", methods=["POST"])
def date_diff():
    """Selisih 2 tanggal. Body: {date1, date2, format} format default '%Y-%m-%d'."""
    body = _body()
    fmt = body.get("format", "%Y-%m-%d")
    try:
        d1 = datetime.strptime(body.get("date1", ""), fmt)
        d2 = datetime.strptime(body.get("date2", ""), fmt)
    except ValueError as e:
        return error_response(f"Format tanggal salah: {e}")

    delta = abs(d2 - d1)
    return ok_response({
        "days": delta.days,
        "weeks": round(delta.days / 7, 2),
        "months_approx": round(delta.days / 30.44, 2),
        "years_approx": round(delta.days / 365.25, 2),
    })


@calc_bp.route("/unit-convert", methods=["POST"])
def unit_convert():
    """Konversi satuan. Body: {value, from_unit, to_unit, category}.
    category: length | weight | data (byte/KB/MB/GB/TB) | temperature
    """
    body = _body()
    value = float(body.get("value", 0))
    fu = body.get("from_unit", "").lower()
    tu = body.get("to_unit", "").lower()
    category = body.get("category", "").lower()

    tables = {
        "length": {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000,
                   "inch": 0.0254, "ft": 0.3048, "yard": 0.9144, "mile": 1609.34},
        "weight": {"mg": 0.000001, "g": 0.001, "kg": 1, "ton": 1000,
                   "oz": 0.0283495, "lb": 0.453592},
        "data": {"byte": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4},
    }

    if category == "temperature":
        if fu == "c" and tu == "f":
            result = value * 9 / 5 + 32
        elif fu == "f" and tu == "c":
            result = (value - 32) * 5 / 9
        elif fu == "c" and tu == "k":
            result = value + 273.15
        elif fu == "k" and tu == "c":
            result = value - 273.15
        elif fu == tu:
            result = value
        else:
            return error_response("Kombinasi satuan suhu tidak didukung (gunakan c/f/k).")
        return ok_response({"result": result})

    table = tables.get(category)
    if not table or fu not in table or tu not in table:
        return error_response(
            f"Kategori/satuan tidak dikenal. Kategori tersedia: {list(tables.keys())} + temperature"
        )

    base_value = value * table[fu]
    result = base_value / table[tu]
    return ok_response({"result": result})


@calc_bp.route("/loan", methods=["POST"])
def loan():
    """Kalkulator cicilan pinjaman (flat & anuitas sederhana).
    Body: {principal, annual_rate_percent, years}."""
    body = _body()
    p = float(body.get("principal", 0))
    rate = float(body.get("annual_rate_percent", 0)) / 100
    years = float(body.get("years", 1))

    n_months = int(years * 12)
    monthly_rate = rate / 12

    if monthly_rate == 0:
        annuity_payment = p / n_months
    else:
        annuity_payment = p * (monthly_rate * (1 + monthly_rate) ** n_months) / \
            ((1 + monthly_rate) ** n_months - 1)

    flat_payment = (p + (p * rate * years)) / n_months

    return ok_response({
        "months": n_months,
        "annuity_monthly_payment": round(annuity_payment, 2),
        "annuity_total_payment": round(annuity_payment * n_months, 2),
        "flat_monthly_payment": round(flat_payment, 2),
        "flat_total_payment": round(flat_payment * n_months, 2),
    })
