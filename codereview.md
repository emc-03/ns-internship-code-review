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

---

## Follow-up Questions

1.  Share your prompts and the AI outputs.

    My initial Prompt and Model setup:

    ## Prompt 1:

    Act as a senior engineer doing a code review.

              Focus: Find the route registration first.
              Look for where /webhook is mounted

              Rule: Do NOT suggest fixes unless I say "Let's Write"
              Mental Model:
              * What → what to look for
              * Where → where in the code to find it
              * Why → why it matters
              * Red Flag → what bad looks like

              Constraints:
              * Plain English only
              * One concept at a time
              * No theory dumps, keep it straighforward.

              Resources: 2 links max
              Provide:
              1. What you're checking
              2. Where to find it in the code
              3. Why it matters
              4. What good looks like
              5. What bad looks like
              6. Common mistakes devs make here
              Output: Short, scannable, practical

    **Copied in Python Code**

# AI Response 1 :

    Code Review — Route Registration

1.  What I'm checking
    Where /webhook is registered and what HTTP method it accepts.

1.  Where to find it
    python@app.post("/webhook")
    def webhook():
    Line 1 of the route block. @app.post is Flask's shorthand decorator — equivalent to @app.route("/webhook", methods=["POST"]).

1.  Why it matters
    The decorator is the front door. It controls what gets in before any of your logic runs. If it's misconfigured, either nothing reaches the handler, or the wrong things do.

1.  What good looks like

Single, explicit method (POST only) ✅
Clean path, no typos ✅
One handler per route ✅

This part is actually fine.

5. What bad looks like

@app.route("/webhook") with no methods= → Flask defaults to GET only, silently rejects POSTs
A catch-all method like methods=["GET", "POST"] on a webhook receiver
The route mounted under a blueprint but the blueprint never registered on app

6. Common mistake devs make here
   Registering the route correctly but running the app behind a reverse proxy (nginx, Cloudflare) that strips or rewrites the path — so /webhook never actually reaches Flask. The code looks right, but requests vanish silently.

Ready for the next concept? I'd move to the signature verification block next — there's something worth looking at there.

## Prompt 2 :

First check for the happy path validation :
Valid signature - happy path

## AI Response 2:

Happy Path — Signature Validation

1. What I'm checking
   What happens when a request arrives with a valid signature — does verify() correctly confirm it and let the request through.

2. Where to find it
   pythondef verify(sig, body: bytes) -> bool:
   expected = hashlib.sha256(
   (WEBHOOK_SECRET + body.decode("utf-8")).encode("utf-8")
   ).hexdigest()
   return expected == sig # simple compare
   And the call site:
   pythonif not verify(sig, raw):
   return ("bad sig", 401)

3. Why it matters
   This is the only thing standing between the open internet and your database writes. If the happy path is broken, every legitimate webhook gets rejected. If it's too loose, bad actors get in.

4. What good looks like

Secret prepended to body, hashed ✅
Returns a boolean ✅
Checked immediately before any payload processing ✅
Request is rejected with 401 if it fails ✅

The logic flow of the happy path is correct.

5. What bad looks like

Signature check happening after payload is parsed or DB is touched
verify() never actually returning False (always passes)
Comparing against the wrong thing (e.g. the raw header value includes a prefix like sha256= that you forgot to strip)

6. Common mistake devs make here
   The vendor often sends the signature as sha256=abc123... — note the prefix. If you compare the full string against your computed hex digest, it will always fail on valid requests and always pass if you strip nothing and the attacker sends no prefix.
   Check what your vendor actually sends in X-Signature.

One quiet issue worth flagging for later — the comparison on line return expected == sig is doing a standard string equality check. That has implications. Ready to look at that next, or move to the payload parsing?

Ready to move to the database block next — there's a critical issue there.

## Prompt 3:

Don't take away the fun with hints of what's wrong, but yes, let's check the database block. Check for duplications, payload storage size checks, mismatches, for example : check to confirm a new user record can be created with fields mapped correctly.
Database Block Review

## AI Response 3:

1. What I'm checking
   How records are inserted — audit log and user upsert — and whether the data flowing in maps correctly to what the database expects.

2. Where to find it
   pythoncur.execute(
   f"INSERT INTO webhook_audit(email, raw_json) VALUES ('{email}', '{raw.decode('utf-8')}')"
   )

cur.execute(
f"INSERT INTO users(email, role) VALUES('{email}', '{role}')"
)

3. Why it matters
   This is where untrusted external data lands in your database. Field mapping, insert logic, and how the values are passed in all determine whether records are created correctly — or at all.

4. What good looks like

Parameterised queries with ? placeholders
Explicit column-to-value mapping that matches the schema
A real upsert (INSERT OR REPLACE / ON CONFLICT) if the intent is to update existing users
A size check before storing raw_json

5. What bad looks like — Red Flags
   🚩 Red Flag 1 — f-string queries
   pythonf"INSERT INTO users(email, role) VALUES('{email}', '{role}')"
   Values from the payload are dropped directly into the query string. The database has no way to tell your data apart from your SQL.
   🚩 Red Flag 2 — The "upsert" isn't one
   pythoncur.execute(
   f"INSERT INTO users(email, role) VALUES('{email}', '{role}')"
   )
   The comment says upsert but this is a plain INSERT. If the email already exists, this either throws an error or creates a duplicate row — depending on whether there's a unique constraint on the schema (which we can't see). Either way, the intent and the code don't match.
   🚩 Red Flag 3 — No size check on raw_json
   pythonf"INSERT INTO webhook_audit(email, raw_json) VALUES ('{email}', '{raw.decode('utf-8')}')"
   raw is the full unvalidated request body. Nothing checks its size before storing it. A large enough payload writes straight to disk unchallenged.
   🚩 Red Flag 4 — role comes from the payload, not your system
   pythonrole = payload.get("role", "user")
   The vendor tells you what role to assign. Your database writes it without question. If the payload says "admin", that's what gets stored.

6. Common mistakes devs make here
   Trusting that the comment describes what the code does. Upsert and INSERT are not the same thing — and in a codebase under review, that gap is where bugs hide.

## Prompt 4:

Do not use the working model for this response. Reply clear and consise bullet point list of errors that affect the DB, in addition to the previous response.

## AI Response 4:

Additional DB Errors

db.commit() is called but db.close() is never called — connection leaks on every request
No transaction rollback if the second INSERT fails — audit log writes but user record doesn't, leaving orphaned rows
get_db() opens a new connection on every call with no pooling — hammers the DB under any real load
email is written to two tables from the same unvalidated string — no format check, no length cap, anything goes in
/tmp/app.db as a default path means the database can be wiped on system restart with no warning
Using the initial model, what additional errors were found in the code snippet. First create a checklist, then add in the mental model12:37 AMFull Error Checklist

No HMAC — raw SHA256 concatenation used instead
Timing attack — == used instead of hmac.compare_digest()
No try/except around json.loads()
f-string queries — direct payload interpolation into SQL
Fake upsert — plain INSERT labelled as upsert
No size check on raw_json before storing
role assigned directly from untrusted payload
db.close() never called — connection leak
No rollback if second INSERT fails — orphaned audit rows
No DB connection pooling — new connection every request
email unvalidated — no format or length check
/tmp/app.db default path — wiped on restart
WEBHOOK_SECRET has a hardcoded default "dev-secret"

Mental Model Per Error

No HMAC

What — hash function used to verify the signature
Where — verify() function
Why — raw SHA256 concatenation is exploitable
Red Flag — hashlib.sha256(WEBHOOK_SECRET + body...)

Timing Attack

What — how the signature comparison is done
Where — return expected == sig
Why — == leaks timing information character by character
Red Flag — any direct == comparison on secrets or signatures

No try/except on json.loads()

What — error handling on body parsing
Where — payload = json.loads(raw.decode("utf-8"))
Why — malformed JSON throws an unhandled 500, leaking stack info
Red Flag — bare parse with no catch block after the trust gate

f-string SQL Queries

What — how values are passed into queries
Where — both cur.execute() calls
Why — payload data lands directly in the query string
Red Flag — any f"... '{variable}'" inside a cur.execute()

Fake Upsert

What — intent vs actual SQL behaviour
Where — second cur.execute(), comment says upsert
Why — plain INSERT duplicates or errors on existing email
Red Flag — INSERT with no ON CONFLICT clause

No Size Check on raw_json

What — validation on body before storage
Where — audit log INSERT
Why — unbounded payload writes straight to disk
Red Flag — raw passed to DB with no length gate

Role From Payload

What — where role value originates
Where — role = payload.get("role", "user")
Why — vendor controls privilege assignment
Red Flag — any privilege field sourced from external input without a whitelist

Connection Leak

What — database connection lifecycle
Where — get_db() and end of webhook()
Why — connection never closed, leaks on every request
Red Flag — no db.close() or context manager in sight

No Rollback

What — transaction integrity across two inserts
Where — between the two cur.execute() calls
Why — first write succeeds, second fails, data is inconsistent
Red Flag — no try/except wrapping a multi-step db.commit()

No Connection Pooling

What — how connections are managed under load
Where — get_db() called fresh every request
Why — creates a new connection per request, not sustainable
Red Flag — sqlite3.connect() called inside the route handler directly

Unvalidated Email

What — input validation on the email field
Where — email = payload.get("email", "")
Why — no format or length check before it hits two tables
Red Flag — raw .get() with no sanitisation feeding into SQL

/tmp DB Path

What — where the database lives
Where — DB_PATH = os.getenv("DB_PATH", "/tmp/app.db")
Why — /tmp is ephemeral, data gone on restart
Red Flag — any production default path pointing to /tmp

Hardcoded Secret Default

What — fallback value for WEBHOOK_SECRET
Where — WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-secret")
Why — if the env var is missing in prod, the app silently uses a known secret
Red Flag — any hardcoded string as a default for a security-critical env var

## Prompt 5:

Which issue do you think should be addressed first ?

## AI Response 5:

The f-string SQL queries.
Every other issue requires an attacker to be clever — wrong HMAC, timing attacks, oversized payloads. This one requires nothing. Any value in email or role directly rewrites your query. It's the lowest skill, highest impact vulnerability in the file, and it's sitting on the route that accepts external data by design.
Everything else is a problem. This one is a door left open.

## Prompt 6:

Are there any constraints with resolving this first in comparison to another

## AI Response 6:

No hard constraints — it's an isolated change, parameterised queries don't depend on anything else being fixed first.
One thing worth being aware of though:

Fixing the f-strings does not fix the fake upsert sitting in the same query. You'd be making a broken INSERT safer, not correct. If you fix the queries and the upsert logic together, that's a natural pairing — same two lines, same time.

## Prompt 7:

Which issue do you think should be addressed first ?

## AI Response 7:

The f-string SQL queries.

Every other issue requires an attacker to be clever — wrong HMAC, timing attacks, oversized payloads. This one requires nothing. Any value in email or role directly rewrites your query. It's the lowest skill, highest impact vulnerability in the file, and it's sitting on the route that accepts external data by design.

Everything else is a problem. This one is a door left open.

## Prompt 8:

Are there any constraints with resolving this first in comparison to another ?

## AI Response 8:

No hard constraints — it's an isolated change, parameterised queries don't depend on anything else being fixed first.

One thing worth being aware of though:

Fixing the f-strings does not fix the fake upsert sitting in the same query. You'd be making a broken INSERT safer, not correct. If you fix the queries and the upsert logic together, that's a natural pairing — same two lines, same time.
Worth deciding if you want to draw that boundary before writing anything.

## Prompt 9:

Refer to the error checklist. Locate the lines of code affected and advise where to place comments. Make a list of comments for review, include watch points.

## AI Response 9:

Comment Placement Guide
Locating Affected Lines
python
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-secret") # LINE 6
DB_PATH = os.getenv("DB_PATH", "/tmp/app.db") # LINE 5

def verify(sig, body: bytes) -> bool: # LINE 13
expected = hashlib.sha256( # LINE 15
(WEBHOOK_SECRET + body.decode("utf-8")).encode()
).hexdigest()
return expected == sig # LINE 18

def webhook(): # LINE 21
raw = request.data # LINE 22
sig = request.headers.get("X-Signature", "") # LINE 23
if not verify(sig, raw): # LINE 25
payload = json.loads(raw.decode("utf-8")) # LINE 28
email = payload.get("email", "") # LINE 31
role = payload.get("role", "user") # LINE 32
db = get_db() # LINE 35
cur.execute(f"INSERT INTO webhook_audit...") # LINE 38
cur.execute(f"INSERT INTO users...") # LINE 43
db.commit() # LINE 46
Comment List
LINE 5 — DB Path

python

# WATCHPOINT: /tmp is ephemeral — wiped on restart

# Set DB_PATH env var explicitly in all environments

DB_PATH = os.getenv("DB_PATH", "/tmp/app.db")
LINE 6 — Hardcoded Secret

python

# WATCHPOINT: fallback is a known string — if env var missing in prod

# this silently passes, app runs with a compromised secret

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-secret")
LINE 15-17 — Wrong Hash Method

python

# REVIEW: this is not HMAC — raw SHA256 concatenation is vulnerable

# to length extension attacks, replace with hmac.new()

expected = hashlib.sha256(
(WEBHOOK_SECRET + body.decode("utf-8")).encode("utf-8")
).hexdigest()
LINE 18 — Timing Attack

python

# REVIEW: == short-circuits on first mismatch

# replace with hmac.compare_digest() to prevent timing attacks

return expected == sig
LINE 28 — No Error Handling

python

# WATCHPOINT: no try/except here — malformed JSON throws unhandled 500

# leaks stack trace in response, wrap in try/except before proceeding

payload = json.loads(raw.decode("utf-8"))
LINE 31 — Unvalidated Email

python

# REVIEW: raw string from payload, no format or length check

# feeds into two tables below — validate before this line

email = payload.get("email", "")
LINE 32 — Role From Payload

python

# WATCHPOINT: privilege assigned by vendor payload directly

# no whitelist check — "admin" in payload means admin in DB

role = payload.get("role", "user")
LINE 35 — No Connection Pooling

python

# REVIEW: new connection opened every request, never pooled

# db.close() also never called below — connection leak on every hit

db = get_db()
LINE 38 — f-string Audit Insert

python

# CRITICAL: f-string interpolation — payload values rewrite the query

# WATCHPOINT: raw body stored with no size check — unbounded disk write

cur.execute(
f"INSERT INTO webhook_audit(email, raw_json) VALUES ('{email}', '{raw.decode('utf-8')}')"
)
LINE 43 — f-string User Insert

python

# CRITICAL: f-string interpolation — same injection risk as above

# REVIEW: plain INSERT labelled as upsert — duplicates or errors on existing email

# no ON CONFLICT clause present

cur.execute(
f"INSERT INTO users(email, role) VALUES('{email}', '{role}')"
)
LINE 46 — No Rollback

python

# WATCHPOINT: commit with no rollback protection

# if line 43 fails, audit row from line 38 is already written

# wrap both inserts in try/except with db.rollback() on failure

db.commit()

Summary Count
Severity Count
CRITICAL 2
WATCHPOINT 6
REVIEW 5

Worth deciding if you want to draw that boundary before writing anything.

---

## Prompt Responses

    - Tell us what you were hoping for the AI to accomplish.
    - Tell us what it actually did.
    - Did you have to re-prompt it based on its output?
    - If you had to change your approach, why?

## Prompt 1:

    I wanted the mental model set early so I wasn't re-explaining the rules every few prompts. It picked up the errors well, flagged them clearly, and threw in some resolution context however, it never told me where in the code the issues actually lived, and it didn't relay necessary comments. For a real code review, both of those are necessary.
    No re-prompting needed, it did what I asked. The problem was what I asked for. The format was too heavy for anyone working against a clock. Looking back, if I'd opened with something closer to what prompt 7 ended up being checklist first, line numbers attached, comments included the whole session could have been tighter and honestly a lot more useful from the start.

## Prompt 2:

      I pasted the code and narrowed the focus to route registration. I wanted to confirm the entry point wasn't misconfigured before anything else. Starting at the front door made sense, but the setup exposed a gap in how I'd opened the session. This was not a re-prompt but a continuation to improve the model.
      It was setup this way to reduce possible errors and any unintentional blending, allowing for better flow control.

## Prompt 3:

      I wanted the signature validation picked apart, specifically verify(), the error handling, and whether the body was being read correctly. It came back with three solid red flags, caught the HMAC gap, the timing attack, and the missing try/except.
      These were all relavant errors, so no re-prompt was needed.
      The one thing that slipped was an unsolicited hint about the database block at the end. A small constraint break, but would still cause error. If I'd been stricter in the original rules about volunteering information, that wouldn't have happened. I could have reprompted, however I chose to see if it picked anything up at the end when I noticed the model wasn't working effectively.

## Prompt 4:

      I wanted the database block walked through properly field mapping, duplication risk, payload storage, and whether the upsert was actually doing what it claimed. It returned four red flags, all on target, and the role privilege catch was a good one I was curious to see if it would spot. I chose not to reprompt at this time, as I was formatting ideas to improve the output.

## Prompt 5:

      I deliberately dropped the mental model entirely and asked for a plain bullet list to see if it would just follow the format switch without pushing back or defaulting to its usual structure. It did, and worked as expected. Five additional issues came back clean. A connection leak, rollback gap, pooling, the /tmp path. All things that hadn't surfaced yet.
      I did reprompt, to include the mental model and adjust for a full picture for Prompt 6. This was more efficient and the checklist made it faster to read and act on.

## Prompt 6:

      I wanted everything consolidated into one place, every error, and mental model was applied to each. Thirteen issues catalogued, format consistent all the way through. I did not reprompt at this stage.
      In hindsight though, this prompt only existed because the earlier structure spread information across too many responses. If the session had been designed better upfront, this consolidation step wouldn't have been necessary at all. I could have included this in Prompt 5, however I wanted to ensure Prompt 5 was going to have a complete list before adding in details.

## Prompt 7:

    I wanted to negate and check for any additional issues, that may have been left out of the checklist. I asked which issue should be addressed first and left it open ended on purpose. I was curious whether it would actually take a position or dodge it.
    It didn't get distracted and identified the f-string SQL. It backed up its reasoning that this needed to be intially addressed from the start and gave a consise response.

## Prompt 8:

    I asked whether fixing the f-strings first would cause any downstream complications. I wanted to see if it would just agree with the direction I'd already set. It didn't agree, and it confirmed no hard dependencies but flagged the upsert as a natural pairing.
    The same lines, same fix window which was actually useful context rather than just validation. I didn't re-prompt.
    The two follow-up questions, prompts 7 and 8 were deliberate. I wanted to make sure the checklist was going to hold up before committing to it, and this error felt like the right one to pressure test that with.

## Prompt 9:

I wanted to keep within the approximate time constraints, so I asked the errors to be mapped to actual lines with comments ready to drop into the file. It came back with every issue located, severity labels attached, and a summary table at the end.
It was what I expected for a handoff document.
I didn't reprompt, as when I scanned over the suggesstions, they seemed to match.
If I'm being honest though, this should have been prompt three.
The session worked, but the shape of it was backwards.
I spent most of the prompts getting to the format that was actually useful, rather than starting there.
I initially focused too much on finding the errors, rather then locating concerns or improvements and then creating follow-up comments.
