"""
utils.py - Helper bersama untuk semua blueprint.
"""
import importlib
import os
import tempfile
import uuid
from pathlib import Path

from flask import jsonify, send_file


def lazy_import(name, pip_name=None):
    """Import modul secara lazy. Kalau belum terinstall, kembalikan error JSON yang jelas."""
    try:
        return importlib.import_module(name)
    except ImportError:
        pip_name = pip_name or name
        raise ModuleNotFoundError(
            f"Modul '{name}' belum terinstall. Jalankan: pip install {pip_name}"
        )


def new_tmp_dir():
    d = os.path.join(tempfile.gettempdir(), "toolkit_pro_" + uuid.uuid4().hex[:10])
    os.makedirs(d, exist_ok=True)
    return d


def save_upload(file_storage, dest_dir=None):
    """Simpan file upload Flask (werkzeug FileStorage) ke disk, kembalikan path-nya."""
    dest_dir = dest_dir or new_tmp_dir()
    filename = file_storage.filename or ("upload_" + uuid.uuid4().hex[:8])
    path = os.path.join(dest_dir, filename)
    file_storage.save(path)
    return path


def error_response(message, code=400):
    return jsonify({"ok": False, "error": str(message)}), code


def ok_response(data=None, message=None):
    payload = {"ok": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return jsonify(payload)


def send_file_response(path, download_name=None, mimetype=None):
    return send_file(
        path,
        as_attachment=True,
        download_name=download_name or os.path.basename(path),
        mimetype=mimetype,
    )
