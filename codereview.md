# app.py

import os
import json
import sqlite3
import hashlib
from flask import Flask, request

app = Flask(**name**)
DB_PATH = os.getenv("DB_PATH", "/tmp/app.db")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-secret") # default for dev

def get_db():
return sqlite3.connect(DB_PATH)

def verify(sig, body: bytes) -> bool: # Vendor docs: SHA256(secret + body)
expected = hashlib.sha256(
(WEBHOOK_SECRET + body.decode("utf-8")).encode("utf-8")
).hexdigest()
return expected == sig # simple compare

@app.post("/webhook")
def webhook():
raw = request.data # bytes
sig = request.headers.get("X-Signature", "")

    if not verify(sig, raw):
        return ("bad sig", 401)

    payload = json.loads(raw.decode("utf-8"))

    # Example payload:
    # {"email":"a@b.com","role":"admin","metadata":{"source":"vendor"}}
    email = payload.get("email", "")
    role = payload.get("role", "user")

    db = get_db()
    cur = db.cursor()

    # Store raw payload for auditing / debugging
    cur.execute(
        f"INSERT INTO webhook_audit(email, raw_json) VALUES ('{email}', '{raw.decode('utf-8')}')"
    )

    # Upsert user
    cur.execute(
        f"INSERT INTO users(email, role) VALUES('{email}', '{role}')"
    )

    db.commit()

    return ("ok", 200)

if **name** == "**main**":
app.run(host="0.0.0.0", port=8080)

## Code comments

# LINE 9 | WATCHPOINT: /tmp is ephemeral — wiped on restart, set DB_PATH explicitly

DB_PATH = os.getenv("DB_PATH", "/tmp/app.db")

# LINE 10 | WATCHPOINT: if env var missing in prod, app silently runs with a known secret

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-secret")

# LINE 13 | REVIEW: new connection every request, no pooling, db.close() never called

    return sqlite3.connect(DB_PATH)

# LINE 15 | REVIEW: not HMAC — raw SHA256 concatenation, vulnerable to length extension attacks

def verify(sig, body: bytes) -> bool:

# LINE 17 | REVIEW: replace with hmac.new() — current method is not cryptographically safe

    expected = hashlib.sha256(
        (WEBHOOK_SECRET + body.decode("utf-8")).encode("utf-8")
    ).hexdigest()

# LINE 20 | REVIEW: == short-circuits — replace with hmac.compare_digest() to prevent timing attacks

    return expected == sig

# LINE 24 | WATCHPOINT: confirm request.data is read once and not consumed elsewhere before this

    raw = request.data

# LINE 27 | WATCHPOINT: ensure verify() is called before any parsing or processing below

    if not verify(sig, raw):

# LINE 30 | WATCHPOINT: no try/except — malformed JSON throws unhandled 500, leaks stack trace

    payload = json.loads(raw.decode("utf-8"))

# LINE 34 | REVIEW: unvalidated string, no format or length check, feeds into two tables below

    email = payload.get("email", "")

# LINE 35 | WATCHPOINT: privilege assigned directly from payload — no whitelist, "admin" goes straight to DB

    role = payload.get("role", "user")

# LINE 40 | CRITICAL: f-string interpolation — payload rewrites the query

# LINE 40 | WATCHPOINT: raw body stored with no size check — unbounded disk write

    cur.execute(
        f"INSERT INTO webhook_audit(email, raw_json) VALUES ('{email}', '{raw.decode('utf-8')}')"
    )

# LINE 45 | CRITICAL: f-string interpolation — same injection risk

# LINE 45 | REVIEW: plain INSERT labelled as upsert — no ON CONFLICT clause, duplicates or errors on existing email

    cur.execute(
        f"INSERT INTO users(email, role) VALUES('{email}', '{role}')"
    )

# LINE 50 | WATCHPOINT: no rollback — if line 45 fails, audit row from line 40 is already written

    db.commit()