"""
compress_tools.py - Data/file compression endpoints.

Mendukung:
  - Arsip: zip, tar.gz (buat & ekstrak, multi-file)
  - Kompresi file tunggal: gzip, bzip2, lzma/xz
  - Kompresi teks langsung (base64 in/out) - berguna untuk kirim data lewat API/network
  - Minify JSON (hemat ukuran payload)
  - CSV <-> Parquet (kompresi kolumnar, jauh lebih kecil untuk data besar)
  - Compare: bandingkan rasio kompresi beberapa algoritma sekaligus

Semua modul kompresi dasar (zip/gzip/bz2/lzma/tar) memakai library bawaan
Python, tidak perlu install tambahan. Untuk Parquet butuh:
    pip install pyarrow
"""
import bz2
import gzip
import io
import lzma
import os
import tarfile
import zipfile
import base64
import json

from flask import Blueprint, request

from utils import lazy_import, save_upload, new_tmp_dir, error_response, send_file_response, ok_response

compress_bp = Blueprint("compress_tools", __name__, url_prefix="/api/compress")


# =====================================================================
# ARSIP: ZIP
# =====================================================================
@compress_bp.route("/zip", methods=["POST"])
def make_zip():
    """Kompres beberapa file jadi 1 arsip .zip. Form field: files (multiple), level (0-9, opsional)."""
    files = request.files.getlist("files")
    if not files:
        return error_response("Minimal 1 file (field 'files').")

    level = request.form.get("level", type=int, default=6)
    tmp = new_tmp_dir()
    out_path = os.path.join(tmp, "archive.zip")

    total_before = 0
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=level) as zf:
        for f in files:
            path = save_upload(f, tmp)
            total_before += os.path.getsize(path)
            zf.write(path, arcname=os.path.basename(path))

    resp = send_file_response(out_path, "archive.zip", "application/zip")
    resp.headers["X-Size-Before"] = str(total_before)
    resp.headers["X-Size-After"] = str(os.path.getsize(out_path))
    return resp


@compress_bp.route("/zip-info", methods=["POST"])
def zip_info():
    """Lihat isi arsip .zip tanpa mengekstrak. Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)

    try:
        with zipfile.ZipFile(path) as zf:
            entries = [{
                "name": info.filename,
                "size_original": info.file_size,
                "size_compressed": info.compress_size,
                "is_dir": info.is_dir(),
            } for info in zf.infolist()]
    except zipfile.BadZipFile:
        return error_response("File bukan arsip .zip yang valid.")

    return ok_response({"entries": entries, "total_files": len(entries)})


@compress_bp.route("/unzip", methods=["POST"])
def unzip():
    """Ekstrak arsip .zip -> dikembalikan sebagai .zip berisi hasil ekstrak (flat).
    Form field: file, password (opsional, untuk zip terkunci)."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    password = request.form.get("password")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    extract_dir = os.path.join(tmp, "extracted")
    os.makedirs(extract_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(path) as zf:
            pwd = password.encode() if password else None
            zf.extractall(extract_dir, pwd=pwd)
    except zipfile.BadZipFile:
        return error_response("File bukan arsip .zip yang valid.")
    except RuntimeError as e:
        return error_response(f"Gagal ekstrak (password salah/dibutuhkan?): {e}", 401)

    out_path = os.path.join(tmp, "extracted.zip")
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, filenames in os.walk(extract_dir):
            for name in filenames:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, extract_dir)
                zf.write(full, arcname=rel)

    return send_file_response(out_path, "extracted.zip", "application/zip")


# =====================================================================
# ARSIP: TAR.GZ
# =====================================================================
@compress_bp.route("/tar-gz", methods=["POST"])
def make_tar_gz():
    """Kompres beberapa file jadi 1 arsip .tar.gz. Form field: files (multiple)."""
    files = request.files.getlist("files")
    if not files:
        return error_response("Minimal 1 file (field 'files').")

    tmp = new_tmp_dir()
    out_path = os.path.join(tmp, "archive.tar.gz")

    total_before = 0
    with tarfile.open(out_path, "w:gz") as tf:
        for f in files:
            path = save_upload(f, tmp)
            total_before += os.path.getsize(path)
            tf.add(path, arcname=os.path.basename(path))

    resp = send_file_response(out_path, "archive.tar.gz", "application/gzip")
    resp.headers["X-Size-Before"] = str(total_before)
    resp.headers["X-Size-After"] = str(os.path.getsize(out_path))
    return resp


@compress_bp.route("/untar", methods=["POST"])
def untar():
    """Ekstrak arsip .tar.gz/.tar -> dikembalikan sebagai .zip berisi hasil ekstrak.
    Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    extract_dir = os.path.join(tmp, "extracted")
    os.makedirs(extract_dir, exist_ok=True)

    try:
        with tarfile.open(path) as tf:
            tf.extractall(extract_dir, filter="data")
    except tarfile.TarError as e:
        return error_response(f"File bukan arsip tar yang valid: {e}")

    out_path = os.path.join(tmp, "extracted.zip")
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, filenames in os.walk(extract_dir):
            for name in filenames:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, extract_dir)
                zf.write(full, arcname=rel)

    return send_file_response(out_path, "extracted.zip", "application/zip")


# =====================================================================
# KOMPRESI FILE TUNGGAL: gzip / bzip2 / lzma
# =====================================================================
_ALGOS = {
    "gzip": (gzip, ".gz"),
    "bzip2": (bz2, ".bz2"),
    "lzma": (lzma, ".xz"),
}


@compress_bp.route("/file-compress", methods=["POST"])
def file_compress():
    """Kompres 1 file. Form field: file, algo (gzip/bzip2/lzma, default gzip)."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    algo = request.form.get("algo", "gzip").lower()
    if algo not in _ALGOS:
        return error_response(f"Algo harus salah satu dari: {list(_ALGOS.keys())}")

    mod, ext = _ALGOS[algo]
    tmp = new_tmp_dir()
    path = save_upload(f, tmp)

    with open(path, "rb") as fi:
        raw = fi.read()
    compressed = mod.compress(raw)

    out_path = os.path.join(tmp, os.path.basename(path) + ext)
    with open(out_path, "wb") as fo:
        fo.write(compressed)

    resp = send_file_response(out_path)
    resp.headers["X-Size-Before"] = str(len(raw))
    resp.headers["X-Size-After"] = str(len(compressed))
    ratio = (1 - len(compressed) / len(raw)) * 100 if raw else 0
    resp.headers["X-Compression-Ratio-Percent"] = f"{ratio:.2f}"
    return resp


@compress_bp.route("/file-decompress", methods=["POST"])
def file_decompress():
    """Dekompres 1 file. Form field: file, algo (gzip/bzip2/lzma, default gzip)."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    algo = request.form.get("algo", "gzip").lower()
    if algo not in _ALGOS:
        return error_response(f"Algo harus salah satu dari: {list(_ALGOS.keys())}")

    mod, ext = _ALGOS[algo]
    tmp = new_tmp_dir()
    path = save_upload(f, tmp)

    with open(path, "rb") as fi:
        raw = fi.read()
    try:
        decompressed = mod.decompress(raw)
    except Exception as e:
        return error_response(f"Gagal dekompres (format/algo salah?): {e}")

    name = os.path.basename(path)
    if name.endswith(ext):
        name = name[: -len(ext)]
    out_path = os.path.join(tmp, name or "decompressed.bin")
    with open(out_path, "wb") as fo:
        fo.write(decompressed)

    return send_file_response(out_path)


# =====================================================================
# KOMPRESI TEKS LANGSUNG (untuk kirim/terima data lewat API/network)
# =====================================================================
@compress_bp.route("/text-compress", methods=["POST"])
def text_compress():
    """Kompres teks -> base64. Body: {text, algo (gzip/bzip2/lzma, default gzip)}."""
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    algo = body.get("algo", "gzip").lower()
    if algo not in _ALGOS:
        return error_response(f"Algo harus salah satu dari: {list(_ALGOS.keys())}")

    mod, _ = _ALGOS[algo]
    raw = text.encode("utf-8")
    compressed = mod.compress(raw)
    b64 = base64.b64encode(compressed).decode("ascii")

    ratio = (1 - len(compressed) / len(raw)) * 100 if raw else 0
    return ok_response({
        "base64": b64,
        "algo": algo,
        "size_before": len(raw),
        "size_after": len(compressed),
        "compression_ratio_percent": round(ratio, 2),
    })


@compress_bp.route("/text-decompress", methods=["POST"])
def text_decompress():
    """Dekompres base64 -> teks asli. Body: {base64, algo}."""
    body = request.get_json(silent=True) or {}
    b64 = body.get("base64", "")
    algo = body.get("algo", "gzip").lower()
    if algo not in _ALGOS:
        return error_response(f"Algo harus salah satu dari: {list(_ALGOS.keys())}")

    mod, _ = _ALGOS[algo]
    try:
        raw = base64.b64decode(b64)
        text = mod.decompress(raw).decode("utf-8")
        return ok_response({"text": text})
    except Exception as e:
        return error_response(f"Gagal dekompres: {e}")


# =====================================================================
# MINIFY JSON (hemat ukuran payload API)
# =====================================================================
@compress_bp.route("/json-minify", methods=["POST"])
def json_minify():
    """Minify JSON (hapus whitespace/indentasi). Body: {text}."""
    body = request.get_json(silent=True) or {}
    raw = body.get("text", "")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        return error_response(f"JSON tidak valid: {e}")

    minified = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
    before, after = len(raw), len(minified)
    ratio = (1 - after / before) * 100 if before else 0
    return ok_response({
        "result": minified,
        "size_before": before,
        "size_after": after,
        "saved_percent": round(ratio, 2),
    })


# =====================================================================
# CSV <-> PARQUET (kompresi kolumnar untuk data besar)
# =====================================================================
@compress_bp.route("/csv-to-parquet", methods=["POST"])
def csv_to_parquet():
    """CSV -> Parquet (kompresi kolumnar, ukuran jauh lebih kecil untuk data besar).
    Form field: file, compression (snappy/gzip/brotli/zstd, default snappy).
    Butuh: pip install pyarrow"""
    pd = lazy_import("pandas")
    lazy_import("pyarrow")  # engine parquet

    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    compression = request.form.get("compression", "snappy")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    df = pd.read_csv(path)

    out_path = os.path.join(tmp, "converted.parquet")
    df.to_parquet(out_path, engine="pyarrow", compression=compression, index=False)

    resp = send_file_response(out_path, "converted.parquet")
    resp.headers["X-Size-Before"] = str(os.path.getsize(path))
    resp.headers["X-Size-After"] = str(os.path.getsize(out_path))
    return resp


@compress_bp.route("/parquet-to-csv", methods=["POST"])
def parquet_to_csv():
    """Parquet -> CSV. Form field: file. Butuh: pip install pyarrow"""
    pd = lazy_import("pandas")
    lazy_import("pyarrow")

    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    df = pd.read_parquet(path, engine="pyarrow")

    out_path = os.path.join(tmp, "converted.csv")
    df.to_csv(out_path, index=False)
    return send_file_response(out_path, "converted.csv", "text/csv")


# =====================================================================
# COMPARE: bandingkan rasio kompresi beberapa algoritma sekaligus
# =====================================================================
@compress_bp.route("/compare", methods=["POST"])
def compare():
    """Bandingkan ukuran hasil kompresi file dengan gzip/bzip2/lzma/zip.
    Form field: file. Berguna untuk memilih algoritma paling optimal."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    with open(path, "rb") as fi:
        raw = fi.read()

    results = {"original_bytes": len(raw)}

    for name, (mod, _) in _ALGOS.items():
        compressed = mod.compress(raw)
        results[name] = {
            "bytes": len(compressed),
            "saved_percent": round((1 - len(compressed) / len(raw)) * 100, 2) if raw else 0,
        }

    # zip (deflate)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(os.path.basename(path), raw)
    zip_size = len(buf.getvalue())
    results["zip_deflate"] = {
        "bytes": zip_size,
        "saved_percent": round((1 - zip_size / len(raw)) * 100, 2) if raw else 0,
    }

    best = min(
        ((k, v["bytes"]) for k, v in results.items() if isinstance(v, dict)),
        key=lambda kv: kv[1],
        default=(None, None),
    )
    results["recommended"] = best[0]

    return ok_response(results)
