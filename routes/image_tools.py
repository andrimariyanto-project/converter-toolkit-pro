"""
image_tools.py - Image processing endpoints.
"""
import base64
import io
import os

from flask import Blueprint, request, jsonify

from utils import lazy_import, save_upload, new_tmp_dir, error_response, send_file_response, ok_response

image_bp = Blueprint("image_tools", __name__, url_prefix="/api/image")


def _open_image(file_storage, tmp):
    PIL = lazy_import("PIL", "pillow")
    from PIL import Image
    path = save_upload(file_storage, tmp)
    return Image.open(path), path


@image_bp.route("/convert", methods=["POST"])
def convert():
    """Convert format gambar. Form field: file, format (jpg/png/webp/bmp/tiff/gif)."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    fmt = request.form.get("format", "png").lower().replace("jpeg", "jpg")
    pil_fmt = "JPEG" if fmt == "jpg" else fmt.upper()

    tmp = new_tmp_dir()
    img, _ = _open_image(f, tmp)
    if pil_fmt == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    out_path = os.path.join(tmp, f"converted.{fmt}")
    img.save(out_path, pil_fmt)
    return send_file_response(out_path, f"converted.{fmt}")


@image_bp.route("/resize", methods=["POST"])
def resize():
    """Resize gambar. Form field: file, width, height, scale (salah satu)."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    PIL = lazy_import("PIL", "pillow")
    from PIL import Image

    tmp = new_tmp_dir()
    img, path = _open_image(f, tmp)
    w, h = img.size

    scale = request.form.get("scale", type=float)
    width = request.form.get("width", type=int)
    height = request.form.get("height", type=int)

    if scale:
        new_size = (int(w * scale), int(h * scale))
    elif width or height:
        ratio = min((width / w) if width else 1, (height / h) if height else 1)
        new_size = (int(w * ratio), int(h * ratio))
    else:
        return error_response("Sertakan salah satu: width, height, atau scale.")

    img = img.resize(new_size, Image.LANCZOS)
    out_path = os.path.join(tmp, "resized_" + os.path.basename(path))
    img.save(out_path)
    return send_file_response(out_path)


@image_bp.route("/compress", methods=["POST"])
def compress():
    """Kompres gambar (quality 1-95). Form field: file, quality (default 70)."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    quality = int(request.form.get("quality", 70))

    tmp = new_tmp_dir()
    img, path = _open_image(f, tmp)
    if img.mode == "RGBA":
        img = img.convert("RGB")

    out_path = os.path.join(tmp, "compressed_" + os.path.splitext(os.path.basename(path))[0] + ".jpg")
    img.save(out_path, "JPEG", quality=quality, optimize=True)

    before = os.path.getsize(path)
    after = os.path.getsize(out_path)
    resp = send_file_response(out_path)
    resp.headers["X-Size-Before"] = str(before)
    resp.headers["X-Size-After"] = str(after)
    return resp


@image_bp.route("/crop", methods=["POST"])
def crop():
    """Crop gambar. Form field: file, x, y, width, height."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    x = request.form.get("x", type=int, default=0)
    y = request.form.get("y", type=int, default=0)
    w = request.form.get("width", type=int)
    h = request.form.get("height", type=int)
    if w is None or h is None:
        return error_response("Field 'width' dan 'height' wajib diisi.")

    tmp = new_tmp_dir()
    img, path = _open_image(f, tmp)
    cropped = img.crop((x, y, x + w, y + h))

    out_path = os.path.join(tmp, "cropped_" + os.path.basename(path))
    cropped.save(out_path)
    return send_file_response(out_path)


@image_bp.route("/rotate", methods=["POST"])
def rotate():
    """Rotasi gambar. Form field: file, degrees."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    degrees = request.form.get("degrees", type=float, default=90)

    tmp = new_tmp_dir()
    img, path = _open_image(f, tmp)
    rotated = img.rotate(-degrees, expand=True)

    out_path = os.path.join(tmp, "rotated_" + os.path.basename(path))
    rotated.save(out_path)
    return send_file_response(out_path)


@image_bp.route("/watermark", methods=["POST"])
def watermark():
    """Tambah watermark teks ke gambar. Form field: file, text."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    text = request.form.get("text", "WATERMARK")

    PIL = lazy_import("PIL", "pillow")
    from PIL import ImageDraw, ImageFont

    tmp = new_tmp_dir()
    img, path = _open_image(f, tmp)
    img = img.convert("RGBA")
    overlay = PIL.Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = max(20, img.width // 20)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = ((img.width - tw) // 2, (img.height - th) // 2)
    draw.text(pos, text, font=font, fill=(255, 255, 255, 128))

    result = PIL.Image.alpha_composite(img, overlay).convert("RGB")
    out_path = os.path.join(tmp, "watermarked_" + os.path.splitext(os.path.basename(path))[0] + ".jpg")
    result.save(out_path, "JPEG", quality=90)
    return send_file_response(out_path)


@image_bp.route("/grayscale", methods=["POST"])
def grayscale():
    """Ubah gambar jadi hitam putih. Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    tmp = new_tmp_dir()
    img, path = _open_image(f, tmp)
    gray = img.convert("L")

    out_path = os.path.join(tmp, "gray_" + os.path.basename(path))
    gray.save(out_path)
    return send_file_response(out_path)


@image_bp.route("/to-base64", methods=["POST"])
def to_base64():
    """Convert gambar -> base64 string. Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    raw = f.read()
    b64 = base64.b64encode(raw).decode("ascii")
    mime = f.mimetype or "image/png"
    return ok_response({
        "base64": b64,
        "data_uri": f"data:{mime};base64,{b64}",
        "size_bytes": len(raw),
    })


@image_bp.route("/from-base64", methods=["POST"])
def from_base64():
    """Convert base64 string -> file gambar. JSON body: {base64, format}."""
    body = request.get_json(silent=True) or {}
    b64 = body.get("base64")
    fmt = body.get("format", "png")
    if not b64:
        return error_response("Field 'base64' wajib diisi (JSON body).")

    if "," in b64 and b64.strip().startswith("data:"):
        b64 = b64.split(",", 1)[1]

    tmp = new_tmp_dir()
    out_path = os.path.join(tmp, f"decoded.{fmt}")
    try:
        raw = base64.b64decode(b64)
    except Exception as e:
        return error_response(f"Base64 tidak valid: {e}")

    with open(out_path, "wb") as fo:
        fo.write(raw)

    return send_file_response(out_path)


@image_bp.route("/exif", methods=["POST"])
def exif():
    """Baca metadata EXIF gambar. Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    PIL = lazy_import("PIL", "pillow")
    from PIL.ExifTags import TAGS

    tmp = new_tmp_dir()
    img, _ = _open_image(f, tmp)
    exif_data = img._getexif() if hasattr(img, "_getexif") else None

    result = {"width": img.width, "height": img.height, "format": img.format, "mode": img.mode}
    if exif_data:
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            result[str(tag)] = str(value)

    return ok_response(result)


@image_bp.route("/strip-exif", methods=["POST"])
def strip_exif():
    """Hapus semua metadata EXIF (untuk privasi). Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    PIL = lazy_import("PIL", "pillow")
    from PIL import Image

    tmp = new_tmp_dir()
    img, path = _open_image(f, tmp)
    data = list(img.getdata())
    clean = Image.new(img.mode, img.size)
    clean.putdata(data)

    out_path = os.path.join(tmp, "clean_" + os.path.basename(path))
    clean.save(out_path)
    return send_file_response(out_path)
