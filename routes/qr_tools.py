"""
qr_tools.py - QR code & barcode endpoints.

Butuh library tambahan (install sekali di lokal):
    pip install "qrcode[pil]" pyzbar python-barcode
Untuk pyzbar juga butuh library sistem 'zbar':
    Ubuntu/Debian : sudo apt install libzbar0
    macOS         : brew install zbar
"""
import io
import os

from flask import Blueprint, request

from utils import lazy_import, save_upload, new_tmp_dir, error_response, send_file_response, ok_response

qr_bp = Blueprint("qr_tools", __name__, url_prefix="/api")


@qr_bp.route("/qr/generate", methods=["POST"])
def qr_generate():
    """Generate QR code dari teks. Body: {text, box_size, border, error_correction (L/M/Q/H)}."""
    qrcode = lazy_import("qrcode")
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    if not text:
        return error_response("Field 'text' wajib diisi.")

    box_size = int(body.get("box_size", 10))
    border = int(body.get("border", 4))
    ec_map = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }
    ec = ec_map.get(body.get("error_correction", "M").upper(), qrcode.constants.ERROR_CORRECT_M)

    qr = qrcode.QRCode(box_size=box_size, border=border, error_correction=ec)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    tmp = new_tmp_dir()
    out_path = os.path.join(tmp, "qrcode.png")
    img.save(out_path)
    return send_file_response(out_path, "qrcode.png", "image/png")


@qr_bp.route("/qr/generate-wifi", methods=["POST"])
def qr_generate_wifi():
    """Generate QR untuk konek Wi-Fi otomatis. Body: {ssid, password, encryption (WPA/WEP/nopass), hidden}."""
    qrcode = lazy_import("qrcode")
    body = request.get_json(silent=True) or {}
    ssid = body.get("ssid", "")
    password = body.get("password", "")
    encryption = body.get("encryption", "WPA")
    hidden = "true" if body.get("hidden") else "false"

    if not ssid:
        return error_response("Field 'ssid' wajib diisi.")

    wifi_string = f"WIFI:T:{encryption};S:{ssid};P:{password};H:{hidden};;"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(wifi_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    tmp = new_tmp_dir()
    out_path = os.path.join(tmp, "wifi_qrcode.png")
    img.save(out_path)
    return send_file_response(out_path, "wifi_qrcode.png", "image/png")


@qr_bp.route("/qr/decode", methods=["POST"])
def qr_decode():
    """Decode/scan QR code dari gambar. Form field: file."""
    pyzbar = lazy_import("pyzbar.pyzbar", "pyzbar")
    PIL = lazy_import("PIL", "pillow")
    from PIL import Image

    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    img = Image.open(path)

    results = pyzbar.decode(img)
    if not results:
        return error_response("Tidak ada QR code / barcode terdeteksi pada gambar.", 404)

    decoded = [{"type": r.type, "data": r.data.decode("utf-8", errors="replace")} for r in results]
    return ok_response({"results": decoded})


@qr_bp.route("/barcode/generate", methods=["POST"])
def barcode_generate():
    """Generate barcode (misal Code128, EAN13). Body: {text, type (default code128)}."""
    barcode_mod = lazy_import("barcode", "python-barcode")
    from barcode.writer import ImageWriter

    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    btype = body.get("type", "code128")
    if not text:
        return error_response("Field 'text' wajib diisi.")

    try:
        writer_class = barcode_mod.get_barcode_class(btype)
    except Exception:
        return error_response(f"Tipe barcode '{btype}' tidak dikenal.")

    tmp = new_tmp_dir()
    out_base = os.path.join(tmp, "barcode")
    obj = writer_class(text, writer=ImageWriter())
    out_path = obj.save(out_base)  # menghasilkan .png
    return send_file_response(out_path, "barcode.png", "image/png")
