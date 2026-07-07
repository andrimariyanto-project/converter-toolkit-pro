"""
text_tools.py - Text & data tool endpoints (untuk programmer/engineer).
Semua endpoint menerima/mengembalikan JSON (application/json).
"""
import base64
import difflib
import hashlib
import json
import re
import urllib.parse
import uuid as uuid_lib
from datetime import datetime, timezone

from flask import Blueprint, request

from utils import lazy_import, error_response, ok_response

text_bp = Blueprint("text_tools", __name__, url_prefix="/api/text")


def _body():
    return request.get_json(silent=True) or {}


@text_bp.route("/json-format", methods=["POST"])
def json_format():
    """Format / pretty-print JSON. Body: {text, indent}."""
    body = _body()
    raw = body.get("text", "")
    indent = body.get("indent", 2)
    try:
        parsed = json.loads(raw)
        formatted = json.dumps(parsed, indent=indent, ensure_ascii=False)
        return ok_response({"result": formatted})
    except json.JSONDecodeError as e:
        return error_response(f"JSON tidak valid: {e}")


@text_bp.route("/json-validate", methods=["POST"])
def json_validate():
    """Validasi JSON. Body: {text}."""
    body = _body()
    raw = body.get("text", "")
    try:
        json.loads(raw)
        return ok_response({"valid": True})
    except json.JSONDecodeError as e:
        return ok_response({"valid": False, "error": str(e)})


@text_bp.route("/base64-encode", methods=["POST"])
def base64_encode():
    """Encode teks -> base64. Body: {text}."""
    body = _body()
    raw = body.get("text", "")
    result = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return ok_response({"result": result})


@text_bp.route("/base64-decode", methods=["POST"])
def base64_decode():
    """Decode base64 -> teks. Body: {text}."""
    body = _body()
    raw = body.get("text", "")
    try:
        result = base64.b64decode(raw).decode("utf-8")
        return ok_response({"result": result})
    except Exception as e:
        return error_response(f"Base64 tidak valid: {e}")


@text_bp.route("/url-encode", methods=["POST"])
def url_encode():
    """URL-encode teks. Body: {text}."""
    body = _body()
    return ok_response({"result": urllib.parse.quote(body.get("text", ""))})


@text_bp.route("/url-decode", methods=["POST"])
def url_decode():
    """URL-decode teks. Body: {text}."""
    body = _body()
    return ok_response({"result": urllib.parse.unquote(body.get("text", ""))})


@text_bp.route("/hash", methods=["POST"])
def hash_text():
    """Hash teks. Body: {text, algo} algo: md5/sha1/sha256/sha512."""
    body = _body()
    raw = body.get("text", "")
    algo = body.get("algo", "sha256").lower()
    if algo not in hashlib.algorithms_available:
        return error_response(f"Algoritma '{algo}' tidak didukung.")
    h = hashlib.new(algo)
    h.update(raw.encode("utf-8"))
    return ok_response({"algo": algo, "result": h.hexdigest()})


@text_bp.route("/uuid", methods=["GET"])
def uuid_generate():
    """Generate UUID v4. Query param: count (default 1)."""
    count = request.args.get("count", default=1, type=int)
    count = max(1, min(count, 100))
    return ok_response({"uuids": [str(uuid_lib.uuid4()) for _ in range(count)]})


@text_bp.route("/diff", methods=["POST"])
def diff():
    """Bandingkan 2 teks (unified diff). Body: {text1, text2}."""
    body = _body()
    t1 = body.get("text1", "").splitlines()
    t2 = body.get("text2", "").splitlines()
    d = list(difflib.unified_diff(t1, t2, lineterm="", fromfile="text1", tofile="text2"))
    ratio = difflib.SequenceMatcher(None, "\n".join(t1), "\n".join(t2)).ratio()
    return ok_response({"diff": "\n".join(d), "similarity": round(ratio, 4)})


@text_bp.route("/case-convert", methods=["POST"])
def case_convert():
    """Convert case. Body: {text, target} target: upper/lower/title/camel/snake/kebab/pascal."""
    body = _body()
    text = body.get("text", "")
    target = body.get("target", "upper").lower()

    words = re.split(r"[\s_\-]+", text.strip())
    words = [w for w in words if w]

    if target == "upper":
        result = text.upper()
    elif target == "lower":
        result = text.lower()
    elif target == "title":
        result = text.title()
    elif target == "camel":
        result = words[0].lower() + "".join(w.capitalize() for w in words[1:]) if words else ""
    elif target == "pascal":
        result = "".join(w.capitalize() for w in words)
    elif target == "snake":
        result = "_".join(w.lower() for w in words)
    elif target == "kebab":
        result = "-".join(w.lower() for w in words)
    else:
        return error_response(f"Target '{target}' tidak dikenal.")

    return ok_response({"result": result})


@text_bp.route("/slugify", methods=["POST"])
def slugify():
    """Ubah teks jadi slug URL-friendly. Body: {text}."""
    body = _body()
    text = body.get("text", "").lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return ok_response({"result": text})


@text_bp.route("/word-count", methods=["POST"])
def word_count():
    """Hitung kata/karakter/baris/kalimat. Body: {text}."""
    body = _body()
    text = body.get("text", "")
    words = text.split()
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    lines = text.splitlines()
    return ok_response({
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "words": len(words),
        "sentences": len(sentences),
        "lines": len(lines) or (1 if text else 0),
    })


@text_bp.route("/lorem-ipsum", methods=["GET"])
def lorem_ipsum():
    """Generate teks lorem ipsum. Query: paragraphs (default 1)."""
    base = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
        "nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
        "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur."
    )
    n = request.args.get("paragraphs", default=1, type=int)
    n = max(1, min(n, 20))
    return ok_response({"result": "\n\n".join([base] * n)})


@text_bp.route("/jwt-decode", methods=["POST"])
def jwt_decode():
    """Decode JWT tanpa verifikasi signature (untuk inspeksi). Body: {token}."""
    jwt = lazy_import("jwt", "pyjwt")
    body = _body()
    token = body.get("token", "")
    try:
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})
        return ok_response({"header": header, "payload": payload})
    except Exception as e:
        return error_response(f"Token tidak valid: {e}")


@text_bp.route("/regex-test", methods=["POST"])
def regex_test():
    """Test regex. Body: {pattern, text, flags (optional: 'i','m','s' gabung boleh)}."""
    body = _body()
    pattern = body.get("pattern", "")
    text = body.get("text", "")
    flag_str = body.get("flags", "")

    flags = 0
    if "i" in flag_str:
        flags |= re.IGNORECASE
    if "m" in flag_str:
        flags |= re.MULTILINE
    if "s" in flag_str:
        flags |= re.DOTALL

    try:
        matches = []
        for m in re.finditer(pattern, text, flags):
            matches.append({
                "match": m.group(0),
                "start": m.start(),
                "end": m.end(),
                "groups": m.groups(),
            })
        return ok_response({"matches": matches, "count": len(matches)})
    except re.error as e:
        return error_response(f"Regex tidak valid: {e}")


@text_bp.route("/timestamp-convert", methods=["POST"])
def timestamp_convert():
    """Konversi epoch <-> tanggal manusia. Body: {value, direction: 'to_date'|'to_epoch', format}."""
    body = _body()
    direction = body.get("direction", "to_date")
    value = body.get("value")
    fmt = body.get("format", "%Y-%m-%d %H:%M:%S")

    try:
        if direction == "to_date":
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
            return ok_response({"result": dt.strftime(fmt), "iso": dt.isoformat()})
        else:
            dt = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            return ok_response({"result": int(dt.timestamp())})
    except Exception as e:
        return error_response(f"Gagal konversi: {e}")


@text_bp.route("/csv-to-json", methods=["POST"])
def csv_to_json():
    """Convert teks CSV -> JSON array. Body: {csv_text, delimiter}."""
    import csv as csv_mod
    import io as io_mod

    body = _body()
    raw = body.get("csv_text", "")
    delim = body.get("delimiter", ",")
    reader = csv_mod.DictReader(io_mod.StringIO(raw), delimiter=delim)
    rows = list(reader)
    return ok_response({"result": rows, "rows": len(rows)})


@text_bp.route("/json-to-csv", methods=["POST"])
def json_to_csv():
    """Convert JSON array of objects -> teks CSV. Body: {json_data}."""
    import csv as csv_mod
    import io as io_mod

    body = _body()
    data = body.get("json_data", [])
    if isinstance(data, str):
        data = json.loads(data)
    if not data:
        return error_response("Data JSON kosong / tidak valid.")

    out = io_mod.StringIO()
    writer = csv_mod.DictWriter(out, fieldnames=list(data[0].keys()))
    writer.writeheader()
    writer.writerows(data)
    return ok_response({"result": out.getvalue()})
