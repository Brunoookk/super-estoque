from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import socket
import sqlite3
import time


ROOT = Path(__file__).resolve().parents[1]
HTML_FILE = ROOT / "index.html"
LEGACY_HTML_FILE = ROOT / "SuperEstoque (4).html"
DATA_DIR = Path(os.environ.get("SUPERESTOQUE_DATA_DIR", ROOT / "backend" / "data"))
DB_FILE = DATA_DIR / "superestoque.db"
SESSION_TTL = 8 * 60 * 60
COOKIE_NAME = "se_session"


def now_ts():
    return int(time.time())


def get_lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def json_response(handler, status, payload, headers=None):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Cache-Control", "no-store")
    for key, value in (headers or {}).items():
        handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(body)


def text_response(handler, status, body, content_type="text/plain; charset=utf-8", headers=None):
    raw = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("X-Content-Type-Options", "nosniff")
    for key, value in (headers or {}).items():
        handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(raw)


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240_000)
    return base64.b64encode(salt).decode(), base64.b64encode(digest).decode()


def verify_password(password, salt_b64, digest_b64):
    salt = base64.b64decode(salt_b64.encode())
    _, test = hash_password(password, salt)
    return hmac.compare_digest(test, digest_b64)


def calc_status(qty, minimum):
    qty = float(qty or 0)
    minimum = float(minimum or 0)
    if qty <= 0:
        return "SEM ESTOQUE"
    if qty < minimum:
        return "COMPRAR"
    if qty == minimum:
        return "NO LIMITE"
    return "OK"


def normalize_movement_type(value):
    cleaned = str(value or "").strip().upper()
    cleaned = cleaned.replace("Í", "I").replace("Ì", "I")
    if cleaned == "SAIDA":
        return "SAÍDA"
    if cleaned == "ENTRADA":
        return "ENTRADA"
    return ""


def load_seed_items():
    html = HTML_FILE.read_text(encoding="utf-8")
    match = re.search(r"const\s+SEED\s*=\s*(\[.*?\]);", html, re.S)
    if not match:
        return []
    return json.loads(match.group(1))


def item_to_dict(row):
    return {
        "id": row["id"],
        "cod": row["cod"],
        "desc": row["description"],
        "qty": row["qty"],
        "min": row["minimum"],
        "loc": row["loc"] or "",
        "end": row["address"] or "",
        "status": row["status"],
        "obs": row["obs"] or "",
        "arm": row["warehouse"] or "",
    }


def movement_to_dict(row):
    return {
        "id": row["id"],
        "dt": row["created_at"],
        "cod": row["cod"],
        "desc": row["description"],
        "tipo": row["movement_type"],
        "qty": row["qty"],
        "resp": row["responsible"],
        "obs": row["notes"] or "",
        "saldo": row["balance"],
        "user": row["username"] or "",
    }


def get_data_version(conn):
    row = conn.execute("SELECT value FROM app_state WHERE key = 'data_version'").fetchone()
    return int(row["value"]) if row else 0


def bump_data_version(conn):
    conn.execute(
        """
        INSERT INTO app_state (key, value)
        VALUES ('data_version', '1')
        ON CONFLICT(key) DO UPDATE SET value = CAST(value AS INTEGER) + 1
        """
    )


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              display_name TEXT NOT NULL,
              role TEXT NOT NULL CHECK (role IN ('admin','employee')),
              salt TEXT NOT NULL,
              password_hash TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
              token TEXT PRIMARY KEY,
              user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              csrf TEXT NOT NULL,
              expires_at INTEGER NOT NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              cod TEXT NOT NULL UNIQUE,
              description TEXT NOT NULL,
              qty REAL NOT NULL DEFAULT 0,
              minimum REAL NOT NULL DEFAULT 1,
              loc TEXT,
              address TEXT,
              status TEXT NOT NULL,
              obs TEXT,
              warehouse TEXT,
              updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS movements (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              item_id INTEGER REFERENCES items(id) ON DELETE SET NULL,
              cod TEXT NOT NULL,
              description TEXT NOT NULL,
              movement_type TEXT NOT NULL CHECK (movement_type IN ('ENTRADA','SAÍDA')),
              qty REAL NOT NULL,
              responsible TEXT NOT NULL,
              notes TEXT,
              balance REAL NOT NULL,
              user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS app_state (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )
        conn.execute("INSERT OR IGNORE INTO app_state (key, value) VALUES ('data_version', '1')")

        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            for username, display, role, password in (
                ("chefe", "Chefe do Estoque", "admin", os.environ.get("SUPERESTOQUE_ADMIN_PASSWORD", secrets.token_urlsafe(18))),
                ("funcionario", "Funcionário Estoque", "employee", os.environ.get("SUPERESTOQUE_EMPLOYEE_PASSWORD", secrets.token_urlsafe(18))),
            ):
                salt, digest = hash_password(password)
                conn.execute(
                    "INSERT INTO users (username, display_name, role, salt, password_hash) VALUES (?,?,?,?,?)",
                    (username, display, role, salt, digest),
                )

        if conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0:
            for item in load_seed_items():
                qty = float(item.get("qty") or 0)
                minimum = float(item.get("min") or 1)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO items
                    (cod, description, qty, minimum, loc, address, status, obs, warehouse)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(item.get("cod", "")).strip(),
                        str(item.get("desc", "")).strip(),
                        qty,
                        minimum,
                        item.get("loc", ""),
                        item.get("end", ""),
                        calc_status(qty, minimum),
                        item.get("obs", ""),
                        item.get("arm", ""),
                    ),
                )


class App(BaseHTTPRequestHandler):
    server_version = "SuperEstoqueBackend/1.0"

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    def security_headers(self):
        return {
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "same-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 1_000_000:
            raise ValueError("Payload muito grande.")
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def cookies(self):
        result = {}
        for part in self.headers.get("Cookie", "").split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1)
                result[key] = value
        return result

    def current_user(self):
        token = self.cookies().get(COOKIE_NAME)
        if not token:
            return None
        with db() as conn:
            row = conn.execute(
                """
                SELECT s.token, s.csrf, s.expires_at, u.id, u.username, u.display_name, u.role, u.active
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ?
                """,
                (token,),
            ).fetchone()
            if not row or row["expires_at"] < now_ts() or not row["active"]:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                return None
            return row

    def require_user(self):
        user = self.current_user()
        if not user:
            json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "Login obrigatório."}, self.security_headers())
            return None
        return user

    def require_csrf(self, user):
        if self.command in ("GET", "HEAD", "OPTIONS"):
            return True
        sent = self.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(sent, user["csrf"]):
            json_response(self, HTTPStatus.FORBIDDEN, {"error": "Token de segurança inválido."}, self.security_headers())
            return False
        return True

    def require_admin(self, user):
        if user["role"] != "admin":
            json_response(self, HTTPStatus.FORBIDDEN, {"error": "Acesso restrito ao chefe/admin."}, self.security_headers())
            return False
        return True

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            html_file = HTML_FILE if HTML_FILE.exists() else LEGACY_HTML_FILE
            html = html_file.read_text(encoding="utf-8")
            headers = self.security_headers()
            headers["Cache-Control"] = "no-store"
            return text_response(self, HTTPStatus.OK, html, "text/html; charset=utf-8", headers)
        if path == "/health":
            return json_response(self, HTTPStatus.OK, {"ok": True}, self.security_headers())
        if path == "/api/me":
            user = self.require_user()
            if not user:
                return
            return json_response(
                self,
                HTTPStatus.OK,
                {"user": self.public_user(user), "csrf": user["csrf"]},
                self.security_headers(),
            )
        if path == "/api/items":
            user = self.require_user()
            if not user:
                return
            with db() as conn:
                rows = conn.execute("SELECT * FROM items ORDER BY description COLLATE NOCASE").fetchall()
                version = get_data_version(conn)
            return json_response(self, HTTPStatus.OK, {"items": [item_to_dict(r) for r in rows], "version": version}, self.security_headers())
        if path == "/api/movements":
            user = self.require_user()
            if not user:
                return
            limit = int(parse_qs(parsed.query).get("limit", ["200"])[0])
            limit = max(1, min(limit, 1000))
            with db() as conn:
                rows = conn.execute(
                    """
                    SELECT m.*, u.username
                    FROM movements m
                    LEFT JOIN users u ON u.id = m.user_id
                    ORDER BY m.id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                version = get_data_version(conn)
            return json_response(self, HTTPStatus.OK, {"movements": [movement_to_dict(r) for r in reversed(rows)], "version": version}, self.security_headers())
        if path == "/api/sync":
            user = self.require_user()
            if not user:
                return
            since = int(parse_qs(parsed.query).get("since", ["0"])[0] or 0)
            with db() as conn:
                version = get_data_version(conn)
                if version <= since:
                    return json_response(self, HTTPStatus.OK, {"changed": False, "version": version}, self.security_headers())
                item_rows = conn.execute("SELECT * FROM items ORDER BY description COLLATE NOCASE").fetchall()
                mov_rows = conn.execute(
                    """
                    SELECT m.*, u.username
                    FROM movements m
                    LEFT JOIN users u ON u.id = m.user_id
                    ORDER BY m.id DESC
                    LIMIT 300
                    """
                ).fetchall()
            return json_response(
                self,
                HTTPStatus.OK,
                {
                    "changed": True,
                    "version": version,
                    "items": [item_to_dict(r) for r in item_rows],
                    "movements": [movement_to_dict(r) for r in reversed(mov_rows)],
                },
                self.security_headers(),
            )
        if path == "/api/admin/users":
            user = self.require_user()
            if not user or not self.require_admin(user):
                return
            with db() as conn:
                rows = conn.execute(
                    "SELECT id, username, display_name, role, active, created_at FROM users ORDER BY username"
                ).fetchall()
            return json_response(self, HTTPStatus.OK, {"users": [dict(r) for r in rows]}, self.security_headers())
        return json_response(self, HTTPStatus.NOT_FOUND, {"error": "Rota não encontrada."}, self.security_headers())

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Length", "0")
            for key, value in self.security_headers().items():
                self.send_header(key, value)
            self.end_headers()
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Length", "0")
        for key, value in self.security_headers().items():
            self.send_header(key, value)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/login":
                return self.login()
            if path == "/api/logout":
                user = self.require_user()
                if not user or not self.require_csrf(user):
                    return
                token = self.cookies().get(COOKIE_NAME)
                with db() as conn:
                    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                return json_response(
                    self,
                    HTTPStatus.OK,
                    {"ok": True},
                    {**self.security_headers(), "Set-Cookie": self.expired_cookie()},
                )
            user = self.require_user()
            if not user or not self.require_csrf(user):
                return
            if path == "/api/items":
                return self.create_item(user)
            if path == "/api/movements":
                return self.create_movement(user)
            if path == "/api/admin/users":
                if not self.require_admin(user):
                    return
                return self.create_user()
        except (ValueError, json.JSONDecodeError) as exc:
            return json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)}, self.security_headers())
        return json_response(self, HTTPStatus.NOT_FOUND, {"error": "Rota não encontrada."}, self.security_headers())

    def do_PUT(self):
        user = self.require_user()
        if not user or not self.require_csrf(user):
            return
        match = re.fullmatch(r"/api/items/(\d+)", urlparse(self.path).path)
        if match:
            return self.update_item(int(match.group(1)))
        match = re.fullmatch(r"/api/admin/users/(\d+)", urlparse(self.path).path)
        if match:
            if not self.require_admin(user):
                return
            return self.update_user(int(match.group(1)), user)
        return json_response(self, HTTPStatus.NOT_FOUND, {"error": "Rota não encontrada."}, self.security_headers())

    def do_DELETE(self):
        user = self.require_user()
        if not user or not self.require_csrf(user):
            return
        match = re.fullmatch(r"/api/items/(\d+)", urlparse(self.path).path)
        if match:
            if user["role"] != "admin":
                return json_response(self, HTTPStatus.FORBIDDEN, {"error": "Apenas o chefe pode excluir itens."}, self.security_headers())
            with db() as conn:
                conn.execute("DELETE FROM items WHERE id = ?", (int(match.group(1)),))
                bump_data_version(conn)
            return json_response(self, HTTPStatus.OK, {"ok": True}, self.security_headers())
        match = re.fullmatch(r"/api/admin/users/(\d+)", urlparse(self.path).path)
        if match:
            if not self.require_admin(user):
                return
            user_id = int(match.group(1))
            if user_id == user["id"]:
                return json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Você não pode desativar seu próprio usuário."}, self.security_headers())
            with db() as conn:
                conn.execute("UPDATE users SET active = 0 WHERE id = ?", (user_id,))
                conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            return json_response(self, HTTPStatus.OK, {"ok": True}, self.security_headers())
        return json_response(self, HTTPStatus.NOT_FOUND, {"error": "Rota não encontrada."}, self.security_headers())

    def public_user(self, row):
        return {
            "id": row["id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "role": row["role"],
        }

    def session_cookie(self, token):
        return f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL}"

    def expired_cookie(self):
        return f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"

    def login(self):
        payload = self.read_json()
        username = str(payload.get("username", "")).strip().lower()
        password = str(payload.get("password", ""))
        if not username or not password:
            raise ValueError("Informe usuário e senha.")
        with db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ? AND active = 1", (username,)).fetchone()
            if not user or not verify_password(password, user["salt"], user["password_hash"]):
                time.sleep(0.35)
                return json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "Usuário ou senha inválidos."}, self.security_headers())
            token = secrets.token_urlsafe(32)
            csrf = secrets.token_urlsafe(32)
            conn.execute(
                "INSERT INTO sessions (token, user_id, csrf, expires_at) VALUES (?,?,?,?)",
                (token, user["id"], csrf, now_ts() + SESSION_TTL),
            )
        return json_response(
            self,
            HTTPStatus.OK,
            {"user": self.public_user(user), "csrf": csrf},
            {**self.security_headers(), "Set-Cookie": self.session_cookie(token)},
        )

    def clean_item_payload(self):
        payload = self.read_json()
        cod = str(payload.get("cod", "")).strip()
        desc = str(payload.get("desc", "")).strip()
        if not cod or not desc:
            raise ValueError("Código e descrição são obrigatórios.")
        qty = float(payload.get("qty") or 0)
        minimum = float(payload.get("min") or 1)
        if qty < 0 or minimum < 0:
            raise ValueError("Quantidade e mínimo não podem ser negativos.")
        return {
            "cod": cod,
            "description": desc,
            "qty": qty,
            "minimum": minimum,
            "loc": str(payload.get("loc", "")).strip(),
            "address": str(payload.get("end", "")).strip(),
            "status": calc_status(qty, minimum),
            "obs": str(payload.get("obs", "")).strip(),
            "warehouse": str(payload.get("arm", "")).strip(),
        }

    def create_item(self, user):
        item = self.clean_item_payload()
        with db() as conn:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO items (cod, description, qty, minimum, loc, address, status, obs, warehouse)
                    VALUES (:cod,:description,:qty,:minimum,:loc,:address,:status,:obs,:warehouse)
                    """,
                    item,
                )
            except sqlite3.IntegrityError:
                return json_response(self, HTTPStatus.CONFLICT, {"error": "Já existe item com este código."}, self.security_headers())
            bump_data_version(conn)
            row = conn.execute("SELECT * FROM items WHERE id = ?", (cur.lastrowid,)).fetchone()
        return json_response(self, HTTPStatus.CREATED, {"item": item_to_dict(row)}, self.security_headers())

    def update_item(self, item_id):
        item = self.clean_item_payload()
        item["id"] = item_id
        with db() as conn:
            try:
                cur = conn.execute(
                    """
                    UPDATE items
                    SET cod=:cod, description=:description, qty=:qty, minimum=:minimum, loc=:loc,
                        address=:address, status=:status, obs=:obs, warehouse=:warehouse,
                        updated_at=datetime('now','localtime')
                    WHERE id=:id
                    """,
                    item,
                )
            except sqlite3.IntegrityError:
                return json_response(self, HTTPStatus.CONFLICT, {"error": "Já existe item com este código."}, self.security_headers())
            if cur.rowcount == 0:
                return json_response(self, HTTPStatus.NOT_FOUND, {"error": "Item não encontrado."}, self.security_headers())
            bump_data_version(conn)
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return json_response(self, HTTPStatus.OK, {"item": item_to_dict(row)}, self.security_headers())

    def create_movement(self, user):
        payload = self.read_json()
        cod = str(payload.get("cod", "")).strip()
        movement_type = normalize_movement_type(payload.get("tipo", ""))
        qty = float(payload.get("qty") or 0)
        responsible = str(payload.get("resp", "")).strip()
        notes = str(payload.get("obs", "")).strip()
        if not cod or movement_type not in ("ENTRADA", "SAÍDA") or qty <= 0 or not responsible:
            raise ValueError("Preencha código, tipo, quantidade e responsável.")
        with db() as conn:
            item = conn.execute("SELECT * FROM items WHERE cod = ?", (cod,)).fetchone()
            if not item:
                return json_response(self, HTTPStatus.NOT_FOUND, {"error": "Código não encontrado no estoque."}, self.security_headers())
            balance = float(item["qty"]) + qty if movement_type == "ENTRADA" else float(item["qty"]) - qty
            status = calc_status(balance, item["minimum"])
            conn.execute("UPDATE items SET qty = ?, status = ?, updated_at=datetime('now','localtime') WHERE id = ?", (balance, status, item["id"]))
            cur = conn.execute(
                """
                INSERT INTO movements (item_id, cod, description, movement_type, qty, responsible, notes, balance, user_id)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (item["id"], item["cod"], item["description"], movement_type, qty, responsible, notes, balance, user["id"]),
            )
            updated = conn.execute("SELECT * FROM items WHERE id = ?", (item["id"],)).fetchone()
            movement = conn.execute(
                """
                SELECT m.*, u.username
                FROM movements m
                LEFT JOIN users u ON u.id = m.user_id
                WHERE m.id = ?
                """,
                (cur.lastrowid,),
            ).fetchone()
            bump_data_version(conn)
        return json_response(self, HTTPStatus.CREATED, {"item": item_to_dict(updated), "movement": movement_to_dict(movement)}, self.security_headers())

    def create_user(self):
        payload = self.read_json()
        username = str(payload.get("username", "")).strip().lower()
        display = str(payload.get("display_name", "")).strip() or username
        role = str(payload.get("role", "employee")).strip()
        password = str(payload.get("password", ""))
        if not re.fullmatch(r"[a-z0-9_.-]{3,32}", username):
            raise ValueError("Usuário deve ter 3 a 32 caracteres e usar letras, números, ponto, hífen ou underline.")
        if role not in ("admin", "employee"):
            raise ValueError("Perfil inválido.")
        if len(password) < 6:
            raise ValueError("Senha deve ter pelo menos 6 caracteres.")
        salt, digest = hash_password(password)
        with db() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO users (username, display_name, role, salt, password_hash) VALUES (?,?,?,?,?)",
                    (username, display, role, salt, digest),
                )
            except sqlite3.IntegrityError:
                return json_response(self, HTTPStatus.CONFLICT, {"error": "Usuário já existe."}, self.security_headers())
            row = conn.execute(
                "SELECT id, username, display_name, role, active, created_at FROM users WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()
        return json_response(self, HTTPStatus.CREATED, {"user": dict(row)}, self.security_headers())

    def update_user(self, user_id, current_user):
        payload = self.read_json()
        display = str(payload.get("display_name", "")).strip()
        role = str(payload.get("role", "employee")).strip()
        active = 1 if payload.get("active", True) else 0
        password = str(payload.get("password", ""))
        if role not in ("admin", "employee"):
            raise ValueError("Perfil inválido.")
        if user_id == current_user["id"] and (role != "admin" or not active):
            raise ValueError("Você não pode remover seu próprio acesso de chefe.")
        with db() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                return json_response(self, HTTPStatus.NOT_FOUND, {"error": "Usuário não encontrado."}, self.security_headers())
            display = display or row["display_name"]
            conn.execute(
                "UPDATE users SET display_name = ?, role = ?, active = ? WHERE id = ?",
                (display, role, active, user_id),
            )
            if password:
                if len(password) < 6:
                    raise ValueError("Senha deve ter pelo menos 6 caracteres.")
                salt, digest = hash_password(password)
                conn.execute("UPDATE users SET salt = ?, password_hash = ? WHERE id = ?", (salt, digest, user_id))
            if not active:
                conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            updated = conn.execute(
                "SELECT id, username, display_name, role, active, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return json_response(self, HTTPStatus.OK, {"user": dict(updated)}, self.security_headers())


def main():
    init_db()
    port = int(os.environ.get("PORT", os.environ.get("SUPERESTOQUE_PORT", "8000")))
    host = os.environ.get("SUPERESTOQUE_HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    server = ThreadingHTTPServer((host, port), App)
    print(f"SuperEstoque backend em http://{host}:{port}")
    if host in ("0.0.0.0", ""):
        print(f"Acesso no celular: http://{get_lan_ip()}:{port}")
    print(f"Banco SQLite em {DB_FILE}")
    print("Credenciais iniciais configuradas por variaveis de ambiente ou geradas automaticamente.")
    server.serve_forever()


if __name__ == "__main__":
    main()

