"""
spreadsheet_tools.py - Excel / CSV / JSON workbook tools.
Untuk data analyst & database expert: convert, clean, merge, query SQL, generate INSERT statements.
"""
import json
import os
import re
import sqlite3

from flask import Blueprint, request

from utils import lazy_import, save_upload, new_tmp_dir, error_response, send_file_response, ok_response

sheet_bp = Blueprint("spreadsheet_tools", __name__, url_prefix="/api/sheet")


def _read_table(path):
    pd = lazy_import("pandas")
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(path)
    elif ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    elif ext == ".json":
        return pd.read_json(path)
    else:
        raise ValueError(f"Format file '{ext}' tidak didukung (gunakan csv/xlsx/json).")


@sheet_bp.route("/csv-to-excel", methods=["POST"])
def csv_to_excel():
    """CSV -> Excel. Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    pd = lazy_import("pandas")
    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    df = pd.read_csv(path)

    out_path = os.path.join(tmp, "converted.xlsx")
    df.to_excel(out_path, index=False)
    return send_file_response(out_path, "converted.xlsx")


@sheet_bp.route("/excel-to-csv", methods=["POST"])
def excel_to_csv():
    """Excel -> CSV. Form field: file, sheet_name (opsional)."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    sheet_name = request.form.get("sheet_name", 0)

    pd = lazy_import("pandas")
    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    df = pd.read_excel(path, sheet_name=sheet_name)

    out_path = os.path.join(tmp, "converted.csv")
    df.to_csv(out_path, index=False)
    return send_file_response(out_path, "converted.csv")


@sheet_bp.route("/excel-to-json", methods=["POST"])
def excel_to_json():
    """Excel -> JSON. Form field: file, sheet_name (opsional)."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    sheet_name = request.form.get("sheet_name", 0)

    pd = lazy_import("pandas")
    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    df = pd.read_excel(path, sheet_name=sheet_name)

    return ok_response(json.loads(df.to_json(orient="records")))


@sheet_bp.route("/json-to-excel", methods=["POST"])
def json_to_excel():
    """JSON array of objects -> Excel. Body: {data: [...]}."""
    pd = lazy_import("pandas")
    body = request.get_json(silent=True) or {}
    data = body.get("data", [])
    if not data:
        return error_response("Field 'data' (array of objects) wajib diisi.")

    df = pd.DataFrame(data)
    tmp = new_tmp_dir()
    out_path = os.path.join(tmp, "converted.xlsx")
    df.to_excel(out_path, index=False)
    return send_file_response(out_path, "converted.xlsx")


@sheet_bp.route("/merge", methods=["POST"])
def merge_files():
    """Gabungkan beberapa CSV/Excel (kolom sama) jadi 1 file. Form field: files (multiple)."""
    pd = lazy_import("pandas")
    files = request.files.getlist("files")
    if len(files) < 2:
        return error_response("Butuh minimal 2 file (field 'files').")

    tmp = new_tmp_dir()
    dfs = []
    for f in files:
        path = save_upload(f, tmp)
        dfs.append(_read_table(path))

    merged = pd.concat(dfs, ignore_index=True)
    out_path = os.path.join(tmp, "merged.xlsx")
    merged.to_excel(out_path, index=False)
    return send_file_response(out_path, "merged.xlsx")


@sheet_bp.route("/clean", methods=["POST"])
def clean_data():
    """Bersihkan data: drop_duplicates & drop_na.
    Form field: file, drop_duplicates ('true'/'false'), drop_na ('true'/'false'), trim_strings."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    drop_dup = request.form.get("drop_duplicates", "true") == "true"
    drop_na = request.form.get("drop_na", "false") == "true"
    trim = request.form.get("trim_strings", "true") == "true"

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    df = _read_table(path)

    before = len(df)
    if trim:
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].astype(str).str.strip()
    if drop_dup:
        df = df.drop_duplicates()
    if drop_na:
        df = df.dropna()
    after = len(df)

    out_path = os.path.join(tmp, "cleaned.xlsx")
    df.to_excel(out_path, index=False)
    resp = send_file_response(out_path, "cleaned.xlsx")
    resp.headers["X-Rows-Before"] = str(before)
    resp.headers["X-Rows-After"] = str(after)
    return resp


@sheet_bp.route("/to-sql-insert", methods=["POST"])
def to_sql_insert():
    """Generate SQL INSERT statements dari CSV/Excel. Form field: file, table_name."""
    f = request.files.get("file")
    table_name = request.form.get("table_name", "my_table")
    if not f:
        return error_response("Field 'file' wajib diisi.")
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
        return error_response("table_name tidak valid (hanya huruf/angka/underscore).")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    df = _read_table(path)

    def sql_val(v):
        if v is None or (isinstance(v, float) and str(v) == "nan"):
            return "NULL"
        if isinstance(v, (int, float)):
            return str(v)
        return "'" + str(v).replace("'", "''") + "'"

    cols = list(df.columns)
    lines = [f"-- Auto-generated INSERT statements for table '{table_name}'"]
    for _, row in df.iterrows():
        values = ", ".join(sql_val(v) for v in row.tolist())
        lines.append(f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({values});")

    out_path = os.path.join(tmp, f"{table_name}_insert.sql")
    with open(out_path, "w", encoding="utf-8") as fo:
        fo.write("\n".join(lines))

    return send_file_response(out_path, f"{table_name}_insert.sql", "text/plain")


@sheet_bp.route("/sql-query", methods=["POST"])
def sql_query():
    """Jalankan query SQL terhadap file CSV/Excel (via SQLite in-memory).
    Form field: file, query, table_name (default 't')."""
    f = request.files.get("file")
    query = request.form.get("query", "")
    table_name = request.form.get("table_name", "t")
    if not f or not query:
        return error_response("Field 'file' dan 'query' wajib diisi.")
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
        return error_response("table_name tidak valid.")
    if not re.match(r"^\s*select\b", query, re.IGNORECASE):
        return error_response("Hanya query SELECT yang diizinkan (read-only).")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    df = _read_table(path)

    conn = sqlite3.connect(":memory:")
    df.to_sql(table_name, conn, index=False, if_exists="replace")
    try:
        cursor = conn.execute(query)
        columns = [d[0] for d in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return ok_response({"columns": columns, "rows": rows, "row_count": len(rows)})
    except sqlite3.Error as e:
        return error_response(f"Query error: {e}")
    finally:
        conn.close()


@sheet_bp.route("/summary", methods=["POST"])
def summary():
    """Ringkasan statistik dasar (mirip describe()) dari file tabular. Form field: file."""
    f = request.files.get("file")
    if not f:
        return error_response("Field 'file' wajib diisi.")

    tmp = new_tmp_dir()
    path = save_upload(f, tmp)
    df = _read_table(path)

    desc = json.loads(df.describe(include="all").to_json())
    return ok_response({
        "rows": len(df),
        "columns": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "null_counts": df.isnull().sum().to_dict(),
        "describe": desc,
    })
