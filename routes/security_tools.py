"""
security_tools.py - Security tool endpoints.
"""
import base64
import hashlib
import os
import secrets
import string

from flask import Blueprint, request

from utils import lazy_import, save_upload, new_tmp_dir, error_response, ok_response

security_bp = Blueprint("security_tools", __name__, url_prefix="/api/security")


def _body():
    return request.get_json(silent=True) or {}


@security_bp.route("/password-generate", methods=["GET"])
def password_generate():
    """Generate password acak & aman. Query: length, symbols, numbers, uppercase, count."""
    length = request.args.get("length", default=16, type=int)
    use_symbols = request.args.get("symbols", default="true") == "true"
    use_numbers = request.args.get("numbers", default="true") == "true"
    use_upper = request.args.get("uppercase", default="true") == "true"
    count = request.args.get("count", default=1, type=int)
    count = max(1, min(count, 50))
    length = max(4, min(length, 128))

    charset = string.ascii_lowercase
    if use_upper:
        charset += string.ascii_uppercase
    if use_numbers:
        charset += string.digits
    if use_symbols:
        charset += "!@#$%^&*()-_=+[]{}"

    passwords = ["".join(secrets.choice(charset) for _ in range(length)) for _ in range(count)]
    return ok_response({"passwords": passwords})


@security_bp.route("/strength-check", methods=["POST"])
def strength_check():
    """Cek kekuatan password sederhana. Body: {password}."""
    body = _body()
    pw = body.get("password", "")

    score = 0
    feedback = []
    if len(pw) >= 12:
        score += 2
    elif len(pw) >= 8:
        score += 1
    else:
        feedback.append("Terlalu pendek, gunakan minimal 8-12 karakter.")

    if any(c.islower() for c in pw):
        score += 1
    if any(c.isupper() for c in pw):
        score += 1
    else:
        feedback.append("Tambahkan huruf kapital.")
    if any(c.isdigit() for c in pw):
        score += 1
    else:
        feedback.append("Tambahkan angka.")
    if any(c in "!@#$%^&*()-_=+[]{}" for c in pw):
        score += 1
    else:
        feedback.append("Tambahkan simbol.")

    levels = ["Sangat Lemah", "Lemah", "Cukup", "Kuat", "Sangat Kuat", "Sangat Kuat"]
    level = levels[min(score, 5)]

    return ok_response({"score": score, "max_score": 6, "level": level, "feedback": feedback})


@security_bp.route("/hash-generate", methods=["POST"])
def hash_generate():
    """Generate hash teks. Body: {text, algo}. Untuk password gunakan pbkdf2 (dengan salt)."""
    body = _body()
    text = body.get("text", "")
    algo = body.get("algo", "sha256").lower()

    if algo == "pbkdf2":
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", text.encode(), salt, 200_000)
        return ok_response({
            "algo": "pbkdf2_sha256",
            "salt_hex": salt.hex(),
            "hash_hex": dk.hex(),
            "note": "Simpan salt bersama hash untuk verifikasi nanti."
        })

    if algo not in hashlib.algorithms_available:
        return error_response(f"Algoritma '{algo}' tidak didukung.")

    h = hashlib.new(algo)
    h.update(text.encode("utf-8"))
    return ok_response({"algo": algo, "hash_hex": h.hexdigest()})


@security_bp.route("/hash-verify", methods=["POST"])
def hash_verify():
    """Verifikasi teks terhadap hash pbkdf2. Body: {text, salt_hex, hash_hex}."""
    body = _body()
    text = body.get("text", "")
    salt = bytes.fromhex(body.get("salt_hex", ""))
    expected = body.get("hash_hex", "")

    dk = hashlib.pbkdf2_hmac("sha256", text.encode(), salt, 200_000)
    match = secrets.compare_digest(dk.hex(), expected)
    return ok_response({"match": match})


@security_bp.route("/encrypt", methods=["POST"])
def encrypt_text():
    """Enkripsi teks simetris dengan password (Fernet/AES). Body: {text, password}."""
    cryptography = lazy_import("cryptography")
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    body = _body()
    text = body.get("text", "")
    password = body.get("password", "")
    if not text or not password:
        return error_response("Field 'text' dan 'password' wajib diisi.")

    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000)
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    token = Fernet(key).encrypt(text.encode())

    return ok_response({
        "encrypted": token.decode(),
        "salt_hex": salt.hex(),
        "note": "Simpan salt_hex, dibutuhkan untuk dekripsi."
    })


@security_bp.route("/decrypt", methods=["POST"])
def decrypt_text():
    """Dekripsi teks. Body: {encrypted, password, salt_hex}."""
    cryptography = lazy_import("cryptography")
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    body = _body()
    encrypted = body.get("encrypted", "")
    password = body.get("password", "")
    salt_hex = body.get("salt_hex", "")

    try:
        salt = bytes.fromhex(salt_hex)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000)
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        plain = Fernet(key).decrypt(encrypted.encode())
        return ok_response({"decrypted": plain.decode()})
    except InvalidToken:
        return error_response("Password salah atau data rusak.", 401)
    except Exception as e:
        return error_response(str(e))


@security_bp.route("/jwt-encode", methods=["POST"])
def jwt_encode():
    """Buat JWT token. Body: {payload (dict), secret, algo (default HS256), expires_in_seconds}."""
    jwt = lazy_import("jwt", "pyjwt")
    import time

    body = _body()
    payload = dict(body.get("payload", {}))
    secret = body.get("secret", "")
    algo = body.get("algo", "HS256")
    expires_in = body.get("expires_in_seconds")

    if not secret:
        return error_response("Field 'secret' wajib diisi.")
    if expires_in:
        payload["exp"] = int(time.time()) + int(expires_in)

    token = jwt.encode(payload, secret, algorithm=algo)
    return ok_response({"token": token})


@security_bp.route("/jwt-decode", methods=["POST"])
def jwt_decode_verify():
    """Decode & verifikasi JWT. Body: {token, secret, algo (default HS256)}."""
    jwt = lazy_import("jwt", "pyjwt")
    body = _body()
    token = body.get("token", "")
    secret = body.get("secret", "")
    algo = body.get("algo", "HS256")

    try:
        payload = jwt.decode(token, secret, algorithms=[algo])
        return ok_response({"payload": payload, "valid": True})
    except jwt.ExpiredSignatureError:
        return ok_response({"valid": False, "error": "Token sudah kedaluwarsa."})
    except jwt.InvalidTokenError as e:
        return ok_response({"valid": False, "error": str(e)})


@security_bp.route("/file-checksum", methods=["POST"])
def file_checksum():
    """Hitung checksum file (md5/sha1/sha256/sha512). Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)

    hashers = {name: hashlib.new(name) for name in ("md5", "sha1", "sha256", "sha512")}
    with open(path, "rb") as fo:
        while chunk := fo.read(8192):
            for h in hashers.values():
                h.update(chunk)

    return ok_response({name: h.hexdigest() for name, h in hashers.items()})
