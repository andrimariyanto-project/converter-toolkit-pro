"""
app.py - Entry point aplikasi Converter Toolkit Pro.

Jalankan:
    python3 app.py
Lalu buka browser ke: http://127.0.0.1:5000
"""
import os

from flask import Flask, render_template, jsonify

from routes.convert_tools import convert_bp
from routes.pdf_tools import pdf_bp
from routes.image_tools import image_bp
from routes.text_tools import text_bp
from routes.calculator_tools import calc_bp
from routes.qr_tools import qr_bp
from routes.security_tools import security_bp
from routes.spreadsheet_tools import sheet_bp
from routes.compress_tools import compress_bp


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB upload limit
    app.url_map.strict_slashes = False

    for bp in (convert_bp, pdf_bp, image_bp, text_bp, calc_bp, qr_bp, security_bp, sheet_bp, compress_bp):
        app.register_blueprint(bp)

    @app.route("/")
    def index():
        # Kelompokkan semua endpoint per blueprint untuk ditampilkan di homepage
        groups = {}
        for rule in app.url_map.iter_rules():
            if rule.endpoint == "static" or rule.rule == "/":
                continue
            module = rule.endpoint.split(".")[0]
            groups.setdefault(module, []).append({
                "path": rule.rule,
                "methods": sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS")),
            })
        for g in groups.values():
            g.sort(key=lambda r: r["path"])
        return render_template("index.html", groups=groups)

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"ok": False, "error": "File terlalu besar (maks 200MB)."}), 413

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"ok": False, "error": "Endpoint tidak ditemukan."}), 404

    @app.errorhandler(ModuleNotFoundError)
    def missing_module(e):
        return jsonify({"ok": False, "error": str(e)}), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
