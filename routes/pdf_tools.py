"""
pdf_tools.py - PDF manipulation endpoints.

Semua endpoint menerima file via multipart/form-data (field 'file' atau 'files'),
dan mengembalikan file hasil (PDF/ZIP/TXT/JSON).
"""
import io
import json
import os
import zipfile
from pathlib import Path

from flask import Blueprint, request, jsonify

from utils import lazy_import, save_upload, new_tmp_dir, error_response, send_file_response, ok_response

pdf_bp = Blueprint("pdf_tools", __name__, url_prefix="/api/pdf")


@pdf_bp.route("/merge", methods=["POST"])
def merge():
    """Gabungkan beberapa PDF jadi 1. Form field: files (multiple)."""
    files = request.files.getlist("files")
    if len(files) < 2:
        return error_response("Butuh minimal 2 file PDF (field 'files').")

    pypdf = lazy_import("pypdf")
    from pypdf import PdfWriter, PdfReader

    tmp = new_tmp_dir()
    writer = PdfWriter()
    for f in files:
        path = save_upload(f, tmp)
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)

    out_path = os.path.join(tmp, "merged.pdf")
    with open(out_path, "wb") as fo:
        writer.write(fo)

    return send_file_response(out_path, "merged.pdf", "application/pdf")


@pdf_bp.route("/split", methods=["POST"])
def split():
    """Pecah PDF per halaman -> zip. Form field: file, optional: ranges='1-3,4-5'."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    pypdf = lazy_import("pypdf")
    from pypdf import PdfWriter, PdfReader

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    reader = PdfReader(path)
    n = len(reader.pages)

    ranges_param = request.form.get("ranges", "").strip()
    ranges = []
    if ranges_param:
        for part in ranges_param.split(","):
            a, b = part.split("-") if "-" in part else (part, part)
            ranges.append((int(a), int(b)))
    else:
        ranges = [(i, i) for i in range(1, n + 1)]

    zip_path = os.path.join(tmp, "split_result.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for start, end in ranges:
            start, end = max(1, start), min(n, end)
            writer = PdfWriter()
            for i in range(start - 1, end):
                writer.add_page(reader.pages[i])
            page_path = os.path.join(tmp, f"page_{start}-{end}.pdf")
            with open(page_path, "wb") as fo:
                writer.write(fo)
            zf.write(page_path, arcname=os.path.basename(page_path))

    return send_file_response(zip_path, "split_result.zip", "application/zip")


@pdf_bp.route("/rotate", methods=["POST"])
def rotate():
    """Rotasi halaman. Form field: file, degrees (default 90), pages (opsional, misal '1,3')."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    degrees = int(request.form.get("degrees", 90))
    pages_param = request.form.get("pages", "").strip()
    target = set(int(x) for x in pages_param.split(",")) if pages_param else None

    pypdf = lazy_import("pypdf")
    from pypdf import PdfWriter, PdfReader

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    reader = PdfReader(path)
    writer = PdfWriter()

    for i, page in enumerate(reader.pages, start=1):
        if target is None or i in target:
            page.rotate(degrees)
        writer.add_page(page)

    out_path = os.path.join(tmp, "rotated.pdf")
    with open(out_path, "wb") as fo:
        writer.write(fo)

    return send_file_response(out_path, "rotated.pdf", "application/pdf")


@pdf_bp.route("/watermark", methods=["POST"])
def watermark():
    """Tambah watermark teks. Form field: file, text (default CONFIDENTIAL)."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    text = request.form.get("text", "CONFIDENTIAL")

    pypdf = lazy_import("pypdf")
    lazy_import("reportlab")
    from pypdf import PdfWriter, PdfReader
    from reportlab.pdfgen import canvas

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    reader = PdfReader(path)
    page0 = reader.pages[0]
    w, h = float(page0.mediabox.width), float(page0.mediabox.height)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.saveState()
    c.setFont("Helvetica-Bold", 40)
    c.setFillGray(0.6, 0.4)
    c.translate(w / 2, h / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, text)
    c.restoreState()
    c.save()
    buf.seek(0)
    wm_page = PdfReader(buf).pages[0]

    writer = PdfWriter()
    for page in reader.pages:
        page.merge_page(wm_page)
        writer.add_page(page)

    out_path = os.path.join(tmp, "watermarked.pdf")
    with open(out_path, "wb") as fo:
        writer.write(fo)

    return send_file_response(out_path, "watermarked.pdf", "application/pdf")


@pdf_bp.route("/encrypt", methods=["POST"])
def encrypt():
    """Kunci PDF dengan password. Form field: file, password."""
    f = request.files.get("file")
    password = request.form.get("password")
    if not f or not password:
        return error_response("Field 'file' dan 'password' wajib diisi.")

    pypdf = lazy_import("pypdf")
    from pypdf import PdfWriter, PdfReader

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    reader = PdfReader(path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)

    out_path = os.path.join(tmp, "locked.pdf")
    with open(out_path, "wb") as fo:
        writer.write(fo)

    return send_file_response(out_path, "locked.pdf", "application/pdf")


@pdf_bp.route("/decrypt", methods=["POST"])
def decrypt():
    """Buka kunci PDF. Form field: file, password."""
    f = request.files.get("file")
    password = request.form.get("password")
    if not f or not password:
        return error_response("Field 'file' dan 'password' wajib diisi.")

    pypdf = lazy_import("pypdf")
    from pypdf import PdfWriter, PdfReader

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    reader = PdfReader(path)
    if reader.is_encrypted:
        ok = reader.decrypt(password)
        if not ok:
            return error_response("Password salah.", 401)

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    out_path = os.path.join(tmp, "unlocked.pdf")
    with open(out_path, "wb") as fo:
        writer.write(fo)

    return send_file_response(out_path, "unlocked.pdf", "application/pdf")


@pdf_bp.route("/extract-images", methods=["POST"])
def extract_images():
    """Ekstrak gambar dalam PDF -> zip. Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    pypdf = lazy_import("pypdf")
    from pypdf import PdfReader

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    reader = PdfReader(path)

    zip_path = os.path.join(tmp, "extracted_images.zip")
    count = 0
    with zipfile.ZipFile(zip_path, "w") as zf:
        for p_idx, page in enumerate(reader.pages, start=1):
            for i_idx, img in enumerate(page.images, start=1):
                name = f"p{p_idx}_img{i_idx}_{img.name}"
                zf.writestr(name, img.data)
                count += 1

    if count == 0:
        return error_response("Tidak ada gambar yang terdeteksi di dalam PDF ini.", 404)

    return send_file_response(zip_path, "extracted_images.zip", "application/zip")


@pdf_bp.route("/extract-text", methods=["POST"])
def extract_text():
    """Ekstrak teks per halaman -> JSON. Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    pdfplumber = lazy_import("pdfplumber")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)

    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            pages.append({"page": i, "text": page.extract_text() or ""})

    return ok_response({"pages": pages, "total_pages": len(pages)})


@pdf_bp.route("/metadata", methods=["POST"])
def metadata():
    """Info & metadata PDF -> JSON. Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    pypdf = lazy_import("pypdf")
    from pypdf import PdfReader

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    reader = PdfReader(path)
    meta = reader.metadata or {}
    p0 = reader.pages[0]

    return ok_response({
        "pages": len(reader.pages),
        "encrypted": reader.is_encrypted,
        "title": getattr(meta, "title", None),
        "author": getattr(meta, "author", None),
        "creator": getattr(meta, "creator", None),
        "subject": getattr(meta, "subject", None),
        "page1_size_pt": {
            "width": float(p0.mediabox.width),
            "height": float(p0.mediabox.height),
        },
    })


@pdf_bp.route("/ocr", methods=["POST"])
def ocr():
    """OCR PDF hasil scan -> JSON teks. Form field: file, lang (default ind+eng)."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    lang = request.form.get("lang", "ind+eng")
    dpi = int(request.form.get("dpi", 300))

    pdf2image = lazy_import("pdf2image")
    pytesseract = lazy_import("pytesseract")
    from pdf2image import convert_from_path

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    images = convert_from_path(path, dpi=dpi)

    pages = []
    for i, img in enumerate(images, start=1):
        try:
            text = pytesseract.image_to_string(img, lang=lang)
        except Exception:
            text = pytesseract.image_to_string(img)
        pages.append({"page": i, "text": text})

    return ok_response({"pages": pages, "total_pages": len(pages)})


@pdf_bp.route("/compress", methods=["POST"])
def compress():
    """Kompres ukuran PDF (hapus duplikasi objek dasar via pypdf). Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    pypdf = lazy_import("pypdf")
    from pypdf import PdfWriter, PdfReader

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    reader = PdfReader(path)
    writer = PdfWriter()
    for page in reader.pages:
        page.compress_content_streams()
        writer.add_page(page)

    out_path = os.path.join(tmp, "compressed.pdf")
    with open(out_path, "wb") as fo:
        writer.write(fo)

    before = os.path.getsize(path)
    after = os.path.getsize(out_path)
    resp = send_file_response(out_path, "compressed.pdf", "application/pdf")
    resp.headers["X-Size-Before"] = str(before)
    resp.headers["X-Size-After"] = str(after)
    return resp
