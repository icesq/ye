"""Async SQLite storage (aiosqlite): one shared connection, serialized by an asyncio lock.

Money is stored as integers in minor units (cents / kopecks) of the shop currency.
Localized texts are JSON objects {lang: text}.
"""
import asyncio
import json
import os
import time
from contextlib import asynccontextmanager

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    lang TEXT,
    balance INTEGER NOT NULL DEFAULT 0,
    referrer_id INTEGER,
    ref_earned INTEGER NOT NULL DEFAULT 0,
    is_banned INTEGER NOT NULL DEFAULT 0,
    ban_until INTEGER NOT NULL DEFAULT 0,
    ban_reason TEXT,
    is_blocked INTEGER NOT NULL DEFAULT 0,
    captcha_ok INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    last_seen INTEGER
);
CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    perms TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    emoji TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '{}',
    image TEXT,
    sort INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    featured INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '{}',
    instruction TEXT NOT NULL DEFAULT '{}',
    image TEXT,
    price INTEGER NOT NULL,
    per INTEGER NOT NULL DEFAULT 1,
    qty_min INTEGER NOT NULL DEFAULT 1,
    qty_max INTEGER NOT NULL DEFAULT 1,
    presets TEXT NOT NULL DEFAULT '',
    unit TEXT NOT NULL DEFAULT '',
    input_kind TEXT NOT NULL DEFAULT '',
    input_prompt TEXT NOT NULL DEFAULT '{}',
    delivery TEXT NOT NULL DEFAULT 'auto',
    webhook TEXT NOT NULL DEFAULT '',
    sort INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    sold INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);

CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_stock_product ON stock(product_id);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL DEFAULT 'product',
    product_id INTEGER,
    product_name TEXT NOT NULL,
    qty INTEGER NOT NULL DEFAULT 1,
    input TEXT,
    price INTEGER NOT NULL,
    discount INTEGER NOT NULL DEFAULT 0,
    promo_code TEXT,
    method TEXT NOT NULL,
    method_id INTEGER,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL,
    invoice_id TEXT,
    pay_url TEXT,
    charge_id TEXT,
    message_id INTEGER,
    content TEXT,
    extra TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL,
    paid_at INTEGER,
    delivered_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status, method_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_charge ON orders(charge_id) WHERE charge_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS pay_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 0,
    sort INTEGER NOT NULL DEFAULT 0,
    fee REAL NOT NULL DEFAULT 0,
    config TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS promo_codes (
    code TEXT PRIMARY KEY COLLATE NOCASE,
    percent INTEGER NOT NULL,
    max_uses INTEGER NOT NULL DEFAULT 0,
    used INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS promo_uses (
    code TEXT NOT NULL COLLATE NOCASE,
    user_id INTEGER NOT NULL,
    order_id INTEGER,
    PRIMARY KEY (code, user_id)
);

CREATE TABLE IF NOT EXISTS balance_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    delta INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_balance_log_user ON balance_log(user_id);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

# Order statuses
CREATED = "created"      # waiting for payment
REVIEW = "review"        # manual payment: receipt sent, waiting for an admin
PAID = "paid"            # payment confirmed, fulfillment in progress
PENDING = "pending"      # paid, waiting for stock or for manual delivery
DELIVERED = "delivered"
REFUNDED = "refunded"
EXPIRED = "expired"      # unpaid invoice expired
CANCELED = "canceled"    # canceled by the user / payment rejected

PAID_STATUSES = (PAID, PENDING, DELIVERED)


def now() -> int:
    return int(time.time())


def loc_get(raw, lang: str, fallback: str = "en") -> str:
    """Pick a localized text from a JSON object: lang -> fallback -> en -> any."""
    if not raw:
        return ""
    try:
        data = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (ValueError, TypeError):
        return str(raw)
    if not isinstance(data, dict):
        return str(data)
    for key in (lang, fallback, "en"):
        if data.get(key):
            return data[key]
    for value in data.values():
        if value:
            return value
    return ""


def loc_set(raw, lang: str, text) -> str:
    try:
        data = json.loads(raw) if raw else {}
        if not isinstance(data, dict):
            data = {}
    except ValueError:
        data = {}
    if text:
        data[lang] = text
    else:
        data.pop(lang, None)
    return json.dumps(data, ensure_ascii=False)


def loc_langs(raw):
    try:
        data = json.loads(raw) if raw else {}
        return [k for k, v in data.items() if v] if isinstance(data, dict) else []
    except ValueError:
        return []


class _Rollback(Exception):
    pass


class _Query:
    """Unlocked query helpers bound to a connection (used inside transactions)."""

    def __init__(self, conn):
        self.conn = conn

    async def exec(self, sql, params=()):
        cur = await self.conn.execute(sql, params)
        try:
            return cur.lastrowid, cur.rowcount
        finally:
            await cur.close()

    async def many(self, sql, seq):
        await self.conn.executemany(sql, seq)

    async def one(self, sql, params=()):
        async with self.conn.execute(sql, params) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None

    async def all(self, sql, params=()):
        async with self.conn.execute(sql, params) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def scalar(self, sql, params=()):
        async with self.conn.execute(sql, params) as cur:
            row = await cur.fetchone()
        return row[0] if row else None


class Database:
    def __init__(self):
        self.conn = None
        self.path = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ core
    async def open(self, path: str):
        await self.close()
        self._lock = asyncio.Lock()
        self.path = path
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = await aiosqlite.connect(path, isolation_level=None, timeout=30)
        self.conn.row_factory = aiosqlite.Row
        # Same tuning as in the reference bots: WAL, no mmap, small page cache, temp data on disk.
        for pragma in ("foreign_keys = ON", "synchronous = NORMAL", "cache_size = -4000",
                       "temp_store = FILE", "mmap_size = 0", "busy_timeout = 5000"):
            await self.conn.execute(f"PRAGMA {pragma}")
        if path != ":memory:":
            await self.conn.execute("PRAGMA journal_mode = WAL")
        await self.conn.executescript(SCHEMA)
        await self._migrate()

    async def _migrate(self):
        """Add columns that appeared in newer versions (keeps old databases working)."""
        for stmt in SCHEMA.split(";"):
            stmt = stmt.strip()
            if not stmt.startswith("CREATE TABLE"):
                continue
            table = stmt.split("EXISTS", 1)[1].split("(", 1)[0].strip()
            body = stmt.split("(", 1)[1].rsplit(")", 1)[0]
            async with self.conn.execute(f"PRAGMA table_info({table})") as cur:
                existing = {row[1] for row in await cur.fetchall()}
            for line in body.split("\n"):
                col = line.strip().rstrip(",")
                if not col or col.upper().startswith(("PRIMARY", "UNIQUE", "FOREIGN")):
                    continue
                if col.split()[0] not in existing and "PRIMARY KEY" not in col:
                    await self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col}")

    async def close(self):
        if self.conn is not None:
            await self.conn.close()
            self.conn = None

    async def checkpoint(self):
        if self.conn is not None and self.path != ":memory:":
            async with self._lock:
                await self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    @asynccontextmanager
    async def tx(self):
        """Serialized atomic transaction. Use the yielded helper for queries inside it."""
        async with self._lock:
            await self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield _Query(self.conn)
            except BaseException:
                await self.conn.execute("ROLLBACK")
                raise
            else:
                await self.conn.execute("COMMIT")

    async def exec(self, sql, params=()):
        async with self._lock:
            return await _Query(self.conn).exec(sql, params)

    async def one(self, sql, params=()):
        async with self._lock:
            return await _Query(self.conn).one(sql, params)

    async def all(self, sql, params=()):
        async with self._lock:
            return await _Query(self.conn).all(sql, params)

    async def scalar(self, sql, params=()):
        async with self._lock:
            return await _Query(self.conn).scalar(sql, params)

    @staticmethod
    def _update_sql(table, allowed, fields):
        bad = [k for k in fields if k not in allowed]
        if bad or not fields:
            raise ValueError(f"bad fields for {table}: {bad or 'none'}")
        return ", ".join(f"{k} = ?" for k in fields), list(fields.values())

    # ----------------------------------------------------------------- users
    async def upsert_user(self, uid, username, first_name, lang):
        """Create or refresh a user. Returns (user, is_new)."""
        ts = now()
        async with self.tx() as q:
            exists = await q.scalar("SELECT 1 FROM users WHERE id = ?", (uid,))
            if exists:
                await q.exec(
                    "UPDATE users SET username = ?, first_name = ?, last_seen = ?, is_blocked = 0 WHERE id = ?",
                    (username, first_name, ts, uid),
                )
            else:
                await q.exec(
                    "INSERT INTO users (id, username, first_name, lang, created_at, last_seen) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (uid, username, first_name, lang, ts, ts),
                )
            user = await q.one("SELECT * FROM users WHERE id = ?", (uid,))
        return user, not exists

    async def get_user(self, uid):
        return await self.one("SELECT * FROM users WHERE id = ?", (uid,))

    async def find_user(self, query: str):
        query = (query or "").strip().lstrip("@")
        if "t.me/" in query:
            query = query.rsplit("/", 1)[-1]
        if not query:
            return None
        if query.lstrip("-").isdigit():
            return await self.get_user(int(query))
        return await self.one("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (query,))

    async def set_user_lang(self, uid, lang):
        await self.exec("UPDATE users SET lang = ? WHERE id = ?", (lang, uid))

    async def set_referrer(self, uid, referrer_id) -> bool:
        if not referrer_id or referrer_id == uid:
            return False
        async with self.tx() as q:
            if not await q.scalar("SELECT 1 FROM users WHERE id = ?", (referrer_id,)):
                return False
            _, changed = await q.exec(
                "UPDATE users SET referrer_id = ? WHERE id = ? AND referrer_id IS NULL", (referrer_id, uid)
            )
        return changed == 1

    async def change_balance(self, uid, delta: int, reason: str) -> int:
        async with self.tx() as q:
            await q.exec("UPDATE users SET balance = balance + ? WHERE id = ?", (delta, uid))
            await q.exec(
                "INSERT INTO balance_log (user_id, delta, reason, created_at) VALUES (?, ?, ?, ?)",
                (uid, delta, reason, now()),
            )
            return await q.scalar("SELECT balance FROM users WHERE id = ?", (uid,)) or 0

    async def add_ref_earned(self, uid, amount: int):
        await self.exec("UPDATE users SET ref_earned = ref_earned + ? WHERE id = ?", (amount, uid))

    async def set_ban(self, uid, banned: bool, until: int = 0, reason: str = None):
        await self.exec(
            "UPDATE users SET is_banned = ?, ban_until = ?, ban_reason = ? WHERE id = ?",
            (1 if banned else 0, until if banned else 0, reason if banned else None, uid),
        )

    async def banned_users(self):
        return await self.all(
            "SELECT id, ban_until FROM users WHERE is_banned = 1 AND (ban_until = 0 OR ban_until > ?)", (now(),)
        )

    async def list_banned(self, limit=50, offset=0):
        return await self.all(
            "SELECT * FROM users WHERE is_banned = 1 ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        )

    async def set_blocked(self, uid, blocked: bool):
        await self.exec("UPDATE users SET is_blocked = ? WHERE id = ?", (1 if blocked else 0, uid))

    async def set_captcha_ok(self, uid):
        await self.exec("UPDATE users SET captcha_ok = 1 WHERE id = ?", (uid,))

    async def broadcast_user_ids(self, segment="all"):
        sql = "SELECT id FROM users WHERE is_banned = 0 AND is_blocked = 0"
        buyers = "SELECT DISTINCT user_id FROM orders WHERE status IN ('paid', 'pending', 'delivered')"
        if segment == "buyers":
            sql += f" AND id IN ({buyers})"
        elif segment == "nonbuyers":
            sql += f" AND id NOT IN ({buyers})"
        rows = await self.all(sql + " ORDER BY id")
        return [r["id"] for r in rows]

    async def count_users(self, since: int = 0) -> int:
        return await self.scalar("SELECT COUNT(*) FROM users WHERE created_at >= ?", (since,)) or 0

    async def count_active_users(self, since: int) -> int:
        return await self.scalar("SELECT COUNT(*) FROM users WHERE last_seen >= ?", (since,)) or 0

    async def count_blocked(self) -> int:
        return await self.scalar("SELECT COUNT(*) FROM users WHERE is_blocked = 1") or 0

    async def count_referrals(self, uid) -> int:
        return await self.scalar("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (uid,)) or 0

    async def user_order_stats(self, uid):
        row = await self.one(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(price), 0) AS spent FROM orders "
            "WHERE user_id = ? AND kind = 'product' AND status IN (?, ?, ?)",
            (uid, *PAID_STATUSES),
        )
        return row["cnt"], row["spent"]

    # ---------------------------------------------------------------- admins
    async def list_admins(self):
        return await self.all("SELECT * FROM admins ORDER BY created_at")

    async def get_admin(self, uid):
        return await self.one("SELECT * FROM admins WHERE user_id = ?", (uid,))

    async def set_admin(self, uid, perms: str):
        await self.exec(
            "INSERT INTO admins (user_id, perms, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET perms = excluded.perms",
            (uid, perms, now()),
        )

    async def remove_admin(self, uid):
        await self.exec("DELETE FROM admins WHERE user_id = ?", (uid,))

    # ------------------------------------------------------------ categories
    CATEGORY_FIELDS = {"parent_id", "name", "emoji", "description", "image", "sort", "is_active", "featured"}

    _CATEGORY_SELECT = (
        "SELECT c.*, "
        "(SELECT COUNT(*) FROM products p WHERE p.category_id = c.id) AS products_total, "
        "(SELECT COUNT(*) FROM products p WHERE p.category_id = c.id AND p.is_active = 1) AS products_active, "
        "(SELECT COUNT(*) FROM categories s WHERE s.parent_id = c.id) AS children_total "
        "FROM categories c"
    )

    async def list_categories(self, parent_id=None, active_only=False):
        if parent_id is None:
            sql, params = self._CATEGORY_SELECT + " WHERE c.parent_id IS NULL", ()
        else:
            sql, params = self._CATEGORY_SELECT + " WHERE c.parent_id = ?", (parent_id,)
        if active_only:
            sql += " AND c.is_active = 1"
        rows = await self.all(sql + " ORDER BY c.sort, c.id", params)
        if active_only:
            rows = [r for r in rows if r["products_active"] or await self._has_visible_children(r["id"])]
        return rows

    async def _has_visible_children(self, cid, depth=0) -> bool:
        if depth > 5:
            return False
        for child in await self.all(self._CATEGORY_SELECT + " WHERE c.parent_id = ? AND c.is_active = 1", (cid,)):
            if child["products_active"] or await self._has_visible_children(child["id"], depth + 1):
                return True
        return False

    async def all_categories(self):
        return await self.all(self._CATEGORY_SELECT + " ORDER BY c.sort, c.id")

    async def featured_categories(self):
        rows = await self.all(
            self._CATEGORY_SELECT + " WHERE c.featured = 1 AND c.is_active = 1 ORDER BY c.sort, c.id")
        return [r for r in rows if r["products_active"] or await self._has_visible_children(r["id"])]

    async def get_category(self, cid):
        return await self.one(self._CATEGORY_SELECT + " WHERE c.id = ?", (cid,))

    async def add_category(self, name, emoji="", parent_id=None, description="{}", image=None, featured=0) -> int:
        async with self.tx() as q:
            sort = (await q.scalar("SELECT COALESCE(MAX(sort), 0) FROM categories") or 0) + 10
            rowid, _ = await q.exec(
                "INSERT INTO categories (parent_id, name, emoji, description, image, sort, featured) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (parent_id, name, emoji, description, image, sort, featured),
            )
        return rowid

    async def update_category(self, cid, **fields):
        sets, values = self._update_sql("categories", self.CATEGORY_FIELDS, fields)
        await self.exec(f"UPDATE categories SET {sets} WHERE id = ?", (*values, cid))

    async def delete_category(self, cid):
        await self.exec("DELETE FROM categories WHERE id = ?", (cid,))

    async def count_categories(self) -> int:
        return await self.scalar("SELECT COUNT(*) FROM categories") or 0

    async def move_category(self, cid, direction: int):
        await self._move("categories", cid, direction, "parent_id")

    async def _move(self, table, row_id, direction, group_col):
        """Swap sort order with the neighbour above (direction=-1) or below (+1)."""
        async with self.tx() as q:
            row = await q.one(f"SELECT * FROM {table} WHERE id = ?", (row_id,))
            if not row:
                return
            if row[group_col] is None:
                rows = await q.all(f"SELECT id FROM {table} WHERE {group_col} IS NULL ORDER BY sort, id")
            else:
                rows = await q.all(f"SELECT id FROM {table} WHERE {group_col} = ? ORDER BY sort, id",
                                   (row[group_col],))
            ids = [r["id"] for r in rows]
            idx = ids.index(row_id)
            new_idx = idx + direction
            if not 0 <= new_idx < len(ids):
                return
            ids[idx], ids[new_idx] = ids[new_idx], ids[idx]
            for pos, rid in enumerate(ids):
                await q.exec(f"UPDATE {table} SET sort = ? WHERE id = ?", ((pos + 1) * 10, rid))

    # -------------------------------------------------------------- products
    PRODUCT_FIELDS = {
        "category_id", "name", "description", "instruction", "image", "price", "per", "qty_min", "qty_max",
        "presets", "unit", "input_kind", "input_prompt", "delivery", "webhook", "sort", "is_active", "sold",
    }
    _PRODUCT_SELECT = (
        "SELECT p.*, (SELECT COUNT(*) FROM stock s WHERE s.product_id = p.id) AS stock FROM products p"
    )

    async def list_products(self, cid, active_only=False):
        sql = self._PRODUCT_SELECT + " WHERE p.category_id = ?"
        if active_only:
            sql += " AND p.is_active = 1"
        return await self.all(sql + " ORDER BY p.sort, p.id", (cid,))

    async def all_products(self):
        return await self.all(self._PRODUCT_SELECT + " ORDER BY p.category_id, p.sort, p.id")

    async def get_product(self, pid):
        return await self.one(self._PRODUCT_SELECT + " WHERE p.id = ?", (pid,))

    async def add_product(self, cid, name, price, **fields) -> int:
        fields = {k: v for k, v in fields.items() if k in self.PRODUCT_FIELDS}
        async with self.tx() as q:
            sort = (await q.scalar(
                "SELECT COALESCE(MAX(sort), 0) FROM products WHERE category_id = ?", (cid,)) or 0) + 10
            fields.update(category_id=cid, name=name, price=price, sort=sort)
            cols = ", ".join(fields)
            marks = ", ".join("?" for _ in fields)
            rowid, _ = await q.exec(f"INSERT INTO products ({cols}) VALUES ({marks})", list(fields.values()))
        return rowid

    async def update_product(self, pid, **fields):
        sets, values = self._update_sql("products", self.PRODUCT_FIELDS, fields)
        await self.exec(f"UPDATE products SET {sets} WHERE id = ?", (*values, pid))

    async def delete_product(self, pid):
        await self.exec("DELETE FROM products WHERE id = ?", (pid,))

    async def move_product(self, pid, direction: int):
        await self._move("products", pid, direction, "category_id")

    async def count_products(self, active_only=False) -> int:
        sql = "SELECT COUNT(*) FROM products" + (" WHERE is_active = 1" if active_only else "")
        return await self.scalar(sql) or 0

    async def empty_stock_products(self):
        return await self.all(
            self._PRODUCT_SELECT + " WHERE p.delivery = 'auto' AND p.is_active = 1 "
            "AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.product_id = p.id) ORDER BY p.id"
        )

    # ----------------------------------------------------------------- stock
    async def add_stock(self, pid, items) -> int:
        items = [i.strip() for i in items if i and i.strip()]
        if not items:
            return 0
        ts = now()
        async with self.tx() as q:
            await q.many(
                "INSERT INTO stock (product_id, content, created_at) VALUES (?, ?, ?)",
                [(pid, item, ts) for item in items],
            )
        return len(items)

    async def stock_count(self, pid) -> int:
        return await self.scalar("SELECT COUNT(*) FROM stock WHERE product_id = ?", (pid,)) or 0

    async def stock_items(self, pid):
        rows = await self.all("SELECT content FROM stock WHERE product_id = ? ORDER BY id", (pid,))
        return [r["content"] for r in rows]

    async def clear_stock(self, pid) -> int:
        _, n = await self.exec("DELETE FROM stock WHERE product_id = ?", (pid,))
        return n

    async def remove_duplicate_stock(self, pid) -> int:
        _, n = await self.exec(
            "DELETE FROM stock WHERE product_id = ? AND id NOT IN "
            "(SELECT MIN(id) FROM stock WHERE product_id = ? GROUP BY content)", (pid, pid)
        )
        return n

    # ---------------------------------------------------------------- orders
    ORDER_FIELDS = {
        "status", "invoice_id", "pay_url", "charge_id", "message_id", "content", "extra",
        "paid_at", "delivered_at", "amount", "currency", "input",
    }
    ORDER_INSERT = {
        "user_id", "kind", "product_id", "product_name", "qty", "input", "price", "discount", "promo_code",
        "method", "method_id", "amount", "currency", "status", "extra",
    }

    async def create_order(self, **fields) -> int:
        fields = {k: v for k, v in fields.items() if k in self.ORDER_INSERT}
        fields.setdefault("status", CREATED)
        fields["created_at"] = now()
        fields["amount"] = str(fields.get("amount", ""))
        cols = ", ".join(fields)
        marks = ", ".join("?" for _ in fields)
        rowid, _ = await self.exec(f"INSERT INTO orders ({cols}) VALUES ({marks})", list(fields.values()))
        return rowid

    async def get_order(self, oid):
        return await self.one("SELECT * FROM orders WHERE id = ?", (oid,))

    async def update_order(self, oid, **fields):
        sets, values = self._update_sql("orders", self.ORDER_FIELDS, fields)
        await self.exec(f"UPDATE orders SET {sets} WHERE id = ?", (*values, oid))

    async def transition_order(self, oid, from_statuses, to_status, **fields) -> bool:
        """Change status only if the order is currently in one of `from_statuses` (atomic)."""
        fields = dict(fields, status=to_status)
        sets, values = self._update_sql("orders", self.ORDER_FIELDS, fields)
        marks = ", ".join("?" for _ in from_statuses)
        _, changed = await self.exec(
            f"UPDATE orders SET {sets} WHERE id = ? AND status IN ({marks})", (*values, oid, *from_statuses)
        )
        return changed == 1

    async def deliver_from_stock(self, oid):
        """Atomically take `qty` oldest stock items for a paid/pending order and mark it delivered.

        Returns the delivered content, or None if not deliverable / not enough stock.
        """
        async with self.tx() as q:
            order = await q.one("SELECT * FROM orders WHERE id = ?", (oid,))
            if not order or order["status"] not in (PAID, PENDING):
                return None
            qty = max(1, int(order["qty"] or 1))
            items = await q.all(
                "SELECT id, content FROM stock WHERE product_id = ? ORDER BY id LIMIT ?", (order["product_id"], qty)
            )
            if len(items) < qty:
                return None
            await q.many("DELETE FROM stock WHERE id = ?", [(i["id"],) for i in items])
            contents = [i["content"] for i in items]
            content = ("\n\n" if any("\n" in c for c in contents) else "\n").join(contents)
            await q.exec(
                "UPDATE orders SET status = ?, content = ?, delivered_at = ? WHERE id = ?",
                (DELIVERED, content, now(), oid),
            )
            await q.exec("UPDATE products SET sold = sold + ? WHERE id = ?", (qty, order["product_id"]))
        return content

    async def mark_delivered(self, oid, content) -> bool:
        async with self.tx() as q:
            _, changed = await q.exec(
                "UPDATE orders SET status = ?, content = ?, delivered_at = ? WHERE id = ? AND status IN (?, ?)",
                (DELIVERED, content, now(), oid, PAID, PENDING),
            )
            if changed == 1:
                await q.exec(
                    "UPDATE products SET sold = sold + 1 WHERE id = (SELECT product_id FROM orders WHERE id = ?)",
                    (oid,),
                )
        return changed == 1

    async def pay_order_from_balance(self, oid, uid, amount: int) -> bool:
        """Debit the balance and mark the order paid in one transaction."""
        try:
            async with self.tx() as q:
                _, changed = await q.exec(
                    "UPDATE users SET balance = balance - ? WHERE id = ? AND balance >= ?", (amount, uid, amount)
                )
                if changed != 1:
                    raise _Rollback()
                _, changed = await q.exec(
                    "UPDATE orders SET status = ?, paid_at = ? WHERE id = ? AND status = ? AND user_id = ?",
                    (PAID, now(), oid, CREATED, uid),
                )
                if changed != 1:
                    raise _Rollback()
                await q.exec(
                    "INSERT INTO balance_log (user_id, delta, reason, created_at) VALUES (?, ?, ?, ?)",
                    (uid, -amount, f"order:{oid}", now()),
                )
        except _Rollback:
            return False
        return True

    async def user_orders(self, uid, limit=10, offset=0):
        return await self.all(
            "SELECT * FROM orders WHERE user_id = ? AND status IN (?, ?, ?, ?, ?) ORDER BY id DESC LIMIT ? OFFSET ?",
            (uid, *PAID_STATUSES, REFUNDED, REVIEW, limit, offset),
        )

    async def count_user_orders(self, uid) -> int:
        return await self.scalar(
            "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status IN (?, ?, ?, ?, ?)",
            (uid, *PAID_STATUSES, REFUNDED, REVIEW),
        ) or 0

    async def count_unpaid(self, uid) -> int:
        return await self.scalar(
            "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = ? AND created_at > ?",
            (uid, CREATED, now() - 3 * 3600),
        ) or 0

    async def orders_with_status(self, status, method_id=None, product_id=None, limit=1000):
        sql, params = "SELECT * FROM orders WHERE status = ?", [status]
        if method_id is not None:
            sql += " AND method_id = ?"
            params.append(method_id)
        if product_id is not None:
            sql += " AND product_id = ?"
            params.append(product_id)
        return await self.all(sql + " ORDER BY id LIMIT ?", (*params, limit))

    async def count_orders_with_status(self, *statuses) -> int:
        marks = ", ".join("?" for _ in statuses)
        return await self.scalar(f"SELECT COUNT(*) FROM orders WHERE status IN ({marks})", statuses) or 0

    async def admin_orders(self, statuses, limit=10, offset=0, user_id=None):
        marks = ", ".join("?" for _ in statuses)
        sql, params = f"SELECT * FROM orders WHERE status IN ({marks})", list(statuses)
        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        return await self.all(sql + " ORDER BY id DESC LIMIT ? OFFSET ?", (*params, limit, offset))

    async def count_admin_orders(self, statuses, user_id=None) -> int:
        marks = ", ".join("?" for _ in statuses)
        sql, params = f"SELECT COUNT(*) FROM orders WHERE status IN ({marks})", list(statuses)
        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        return await self.scalar(sql, params) or 0

    async def stale_orders(self, older_than: int):
        return await self.all("SELECT * FROM orders WHERE status = ? AND created_at < ?", (CREATED, older_than))

    async def sales_stats(self, since: int = 0):
        row = await self.one(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(price), 0) AS revenue FROM orders "
            "WHERE kind = 'product' AND status IN (?, ?, ?) AND COALESCE(paid_at, created_at) >= ?",
            (*PAID_STATUSES, since),
        )
        topups = await self.one(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(price), 0) AS total FROM orders "
            "WHERE kind = 'topup' AND status IN (?, ?, ?) AND COALESCE(paid_at, created_at) >= ?",
            (*PAID_STATUSES, since),
        )
        by_method = await self.all(
            "SELECT method, method_id, COUNT(*) AS cnt, COALESCE(SUM(price), 0) AS revenue FROM orders "
            "WHERE status IN (?, ?, ?) AND COALESCE(paid_at, created_at) >= ? "
            "GROUP BY method_id ORDER BY revenue DESC",
            (*PAID_STATUSES, since),
        )
        return {"orders": row["cnt"], "revenue": row["revenue"], "topups": topups["cnt"],
                "topup_total": topups["total"], "by_method": by_method}

    async def top_products(self, since=0, limit=5):
        return await self.all(
            "SELECT product_name, COUNT(*) AS cnt, COALESCE(SUM(price), 0) AS revenue FROM orders "
            "WHERE kind = 'product' AND status IN (?, ?, ?) AND COALESCE(paid_at, created_at) >= ? "
            "GROUP BY product_id ORDER BY revenue DESC LIMIT ?",
            (*PAID_STATUSES, since, limit),
        )

    # ----------------------------------------------------------- pay methods
    METHOD_FIELDS = {"type", "title", "enabled", "sort", "fee", "config"}

    async def list_methods(self, enabled_only=False):
        sql = "SELECT * FROM pay_methods" + (" WHERE enabled = 1" if enabled_only else "")
        return await self.all(sql + " ORDER BY sort, id")

    async def get_method(self, mid):
        return await self.one("SELECT * FROM pay_methods WHERE id = ?", (mid,))

    async def add_method(self, type_, title, config="{}", enabled=0, fee=0) -> int:
        async with self.tx() as q:
            sort = (await q.scalar("SELECT COALESCE(MAX(sort), 0) FROM pay_methods") or 0) + 10
            rowid, _ = await q.exec(
                "INSERT INTO pay_methods (type, title, enabled, sort, fee, config) VALUES (?, ?, ?, ?, ?, ?)",
                (type_, title, enabled, sort, fee, config),
            )
        return rowid

    async def update_method(self, mid, **fields):
        sets, values = self._update_sql("pay_methods", self.METHOD_FIELDS, fields)
        await self.exec(f"UPDATE pay_methods SET {sets} WHERE id = ?", (*values, mid))

    async def delete_method(self, mid):
        await self.exec("DELETE FROM pay_methods WHERE id = ?", (mid,))

    async def move_method(self, mid, direction):
        async with self.tx() as q:
            ids = [r["id"] for r in await q.all("SELECT id FROM pay_methods ORDER BY sort, id")]
            if mid not in ids:
                return
            idx = ids.index(mid)
            new_idx = idx + direction
            if not 0 <= new_idx < len(ids):
                return
            ids[idx], ids[new_idx] = ids[new_idx], ids[idx]
            for pos, rid in enumerate(ids):
                await q.exec("UPDATE pay_methods SET sort = ? WHERE id = ?", ((pos + 1) * 10, rid))

    # ----------------------------------------------------------------- promo
    async def add_promo(self, code, percent, max_uses=0):
        await self.exec(
            "INSERT INTO promo_codes (code, percent, max_uses, used, is_active, created_at) "
            "VALUES (?, ?, ?, 0, 1, ?) "
            "ON CONFLICT(code) DO UPDATE SET percent = excluded.percent, max_uses = excluded.max_uses, is_active = 1",
            (code, percent, max_uses, now()),
        )

    async def get_promo(self, code):
        return await self.one("SELECT * FROM promo_codes WHERE code = ?", (code,))

    async def list_promos(self):
        return await self.all("SELECT * FROM promo_codes ORDER BY created_at DESC, code")

    async def set_promo_active(self, code, active: bool):
        await self.exec("UPDATE promo_codes SET is_active = ? WHERE code = ?", (1 if active else 0, code))

    async def delete_promo(self, code):
        async with self.tx() as q:
            await q.exec("DELETE FROM promo_codes WHERE code = ?", (code,))
            await q.exec("DELETE FROM promo_uses WHERE code = ?", (code,))

    async def promo_used_by(self, code, uid) -> bool:
        return bool(await self.scalar("SELECT 1 FROM promo_uses WHERE code = ? AND user_id = ?", (code, uid)))

    async def consume_promo(self, code, uid, order_id):
        async with self.tx() as q:
            _, inserted = await q.exec(
                "INSERT OR IGNORE INTO promo_uses (code, user_id, order_id) VALUES (?, ?, ?)", (code, uid, order_id)
            )
            if inserted == 1:
                await q.exec("UPDATE promo_codes SET used = used + 1 WHERE code = ?", (code,))

    # -------------------------------------------------------------- settings
    async def all_settings(self):
        return {r["key"]: r["value"] for r in await self.all("SELECT key, value FROM settings")}

    async def set_setting(self, key, value):
        if value is None:
            await self.exec("DELETE FROM settings WHERE key = ?", (key,))
        else:
            await self.exec("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))

    def size_mb(self) -> float:
        try:
            return os.path.getsize(self.path) / 1048576 if self.path and self.path != ":memory:" else 0.0
        except OSError:
            return 0.0
