#!/usr/bin/env python3
# collect_receipts.py, the engine of the MAKERS "receipts" skill (a free gift).
# Python 3.8 or newer, standard library only. Nothing to pip install.
#
# What it does: reads ONE month of the owner's Gmail over IMAP with a Google app password,
# finds receipt and invoice emails, saves their PDF (or photo) files into
#   ~/קבלות/YYYY-MM/
# with clear names, and writes a list of everything it found next to them (רשימה.csv).
#
# Read only, by construction: the mailbox is opened with EXAMINE (select readonly) and every
# message is fetched with BODY.PEEK, so nothing is marked read, moved, labelled or deleted.
# It never sends mail. The app password lives only in ~/.receipts-skill/ on this computer.
#
# Commands (the skill runs them; the owner never has to type them):
#   status                              READY <email> | SETUP_NEEDED <what is missing>
#   setup --email E [--password P]      saves the address; creates the password file and opens it in a text editor
#   check                               logs in once: OK ... | ERROR <CODE> <hint>
#   collect --month YYYY-MM [--no-links] [--max N]
#   summary --month YYYY-MM             the closing lines of collect again, from disk, no network
#   keep --month YYYY-MM --id ID        saves the email itself as the document (receipts with no file and no link)
#   mark --month YYYY-MM --id ID --as income|not-receipt|receipt   moves that email's files into a subfolder, or back
#   open [--month YYYY-MM]              opens the folder in Finder (Mac) or File Explorer (Windows)
#   selftest                            offline checks, no network and no Gmail
#
# Overrides for testing: RECEIPTS_SETTINGS_DIR, RECEIPTS_ROOT.

import argparse
import csv
import datetime as dt
import email
import email.policy
import hashlib
import html
import imaplib
import ipaddress
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
from email.utils import parseaddr, parsedate_to_datetime

VERSION = "1.0"
HOME = os.path.expanduser("~")
SETTINGS = os.environ.get("RECEIPTS_SETTINGS_DIR") or os.path.join(HOME, ".receipts-skill")
ROOT = os.environ.get("RECEIPTS_ROOT") or os.path.join(HOME, "קבלות")
EMAIL_FILE = os.path.join(SETTINGS, "email.txt")
PW_FILE = os.path.join(SETTINGS, "gmail-password.txt")
LIST_NAME = "רשימה.csv"
PAGE_NAME = "רשימה.html"
MANIFEST = ".manifest.json"
BODIES = ".emails"

# What the Gmail search asks for. Gmail also searches inside PDF attachments.
KEYWORDS = ('{קבלה קבלות הקבלה הקבלות חשבונית חשבוניות החשבונית החשבוניות "חשבונית מס" "חשבונית מס קבלה" "חשבון עסקה" "אישור תשלום" '
            'receipt invoice "tax invoice" "payment receipt" "payment confirmation" "order receipt"}')

# A link counts as a document only with a strong word: "receipt" alone also names links like Apple's
# "Turn Off Renewal Receipt Emails", and opening that link is an action, not a download (replay of a real September 2026).
DOC_HINT = re.compile(r"pdf|download|document|להורדה|הורדה|להוריד|מסמך|לצפייה ב|view (?:your |the )?(?:invoice|receipt|bill|document)", re.I)
SKIP_LINK = re.compile(
    r"unsubscribe|optout|opt-out|preferences|privacy|terms|הסר|הסרה|ביטול|facebook\.com|instagram\.com|"
    r"twitter\.com|//x\.com|linkedin\.com|youtube\.com|wa\.me|whatsapp|apps\.apple\.com|play\.google\.com|"
    r"log.?in|sign.?in|password|reset|confirm|verify|approve|cancel|toggle|turn.?off|disable|manage|subscription|settings|"
    r"stop|pause|remov|delet|declin|reject|accept|agree|rsvp|claim|redeem|activat|unlock|vote|"
    r"help|support|contact|faq|feedback|survey|הגדרות|תמיכה|צור קשר|התחבר|כניסה|הפסק|השה|מחיק|למחוק", re.I)
HREF = re.compile(r"""<a\b[^>]*?href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>""", re.I | re.S)
BARE_URL = re.compile(r"""https?://[^\s<>"'\])]+""")
SECRET_LINE = re.compile(r"סיסמ|password|passcode|קוד\s*ה?אימות|חד[ -]?פעמי|verification code|security code|one-time|OTP", re.I)
RECEIPT_SUBJECT = re.compile(r"receipt|invoice|purchase|order|payment|קבלה|חשבונית|חשבון|הזמנה|תשלום|רכישה", re.I)
CARD_NUM = re.compile(r"\b(?:\d[ -]?){12,19}\b")
MAX_LINK_BYTES = 10 * 1024 * 1024
NO_SCRIPT = ('<meta http-equiv="Content-Security-Policy" content="script-src \'none\'; object-src \'none\'; '
             'form-action \'none\'; base-uri \'none\'">\n')


def out(*parts):
    print(" ".join(str(p) for p in parts), flush=True)


def fail(code, hint, exit_code=2):
    out("ERROR", code, hint)
    sys.exit(exit_code)


# ---------- settings ----------

def read_email():
    try:
        with open(EMAIL_FILE, encoding="utf-8-sig") as f:
            return f.read().strip()
    except OSError:
        return ""


def parse_password(text):
    """The app password is 16 letters. Google shows it in four groups with spaces; spaces and comment lines are ignored."""
    lines = [l for l in text.replace("﻿", "").splitlines() if not l.strip().startswith("#")]
    return re.sub(r"\s+", "", "".join(lines))


def read_password():
    try:
        with open(PW_FILE, "rb") as f:
            raw = f.read()
    except OSError:
        return ""
    # Notepad can save as UTF-16 ("Unicode"); TextEdit as UTF-8. Either way it is the same 16 letters.
    enc = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    return parse_password(raw.decode(enc, "replace"))


def password_problem(pw):
    if not pw:
        return "password-file-empty"
    if not re.fullmatch(r"[A-Za-z]{16}", pw):
        return "password-looks-wrong-should-be-16-letters-got-%d-characters" % len(pw)
    return ""


def private_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    if os.name == "posix":
        os.chmod(path, 0o600)


def open_in_editor(path):
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-e", path])
        elif sys.platform.startswith("win"):
            subprocess.Popen(["notepad.exe", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def open_folder(path):
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif sys.platform.startswith("win"):
            os.startfile(path)  # File Explorer
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


# ---------- network ----------

_CTX = None


def ssl_ctx():
    """Verified TLS. Python from python.org on a Mac ships without root certificates; borrow the system ones."""
    global _CTX
    if _CTX:
        return _CTX
    ctx = ssl.create_default_context()
    if sys.platform == "darwin" and not ctx.get_ca_certs():
        pem = os.path.join(SETTINGS, "mac-roots.pem")
        try:
            if not os.path.exists(pem):
                res = subprocess.run(["security", "find-certificate", "-a", "-p",
                                      "/System/Library/Keychains/SystemRootCertificates.keychain"],
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30)
                os.makedirs(SETTINGS, exist_ok=True)
                with open(pem, "wb") as f:
                    f.write(res.stdout)
            ctx.load_verify_locations(cafile=pem)
        except Exception:
            pass
    _CTX = ctx
    return ctx


def login():
    addr, pw = read_email(), read_password()
    if not addr:
        fail("NO_EMAIL", "run setup --email first")
    prob = password_problem(pw)
    if prob:
        fail("PASSWORD", prob)
    socket.setdefaulttimeout(60)
    try:
        M = imaplib.IMAP4_SSL("imap.gmail.com", 993, ssl_context=ssl_ctx())
    except ssl.SSLError as e:
        fail("SSL", "secure connection failed (%s)" % e.__class__.__name__)
    except OSError as e:
        fail("NETWORK", "cannot reach imap.gmail.com (%s). Check the internet connection, VPN or office firewall." % e.__class__.__name__)
    try:
        M.login(addr, pw)
    except imaplib.IMAP4.error as e:
        msg = str(e)
        if "Application-specific password required" in msg:
            fail("APP_PASSWORD_REQUIRED", "this is the regular Google password; an app password (16 letters) is needed")
        if "not enabled for IMAP" in msg:
            fail("IMAP_DISABLED", "Gmail settings > See all settings > Forwarding and POP/IMAP > Enable IMAP")
        if "WEBALERT" in msg or "Web login required" in msg:
            fail("WEB_LOGIN_REQUIRED", "Google wants a normal sign-in in the browser first; sign in to Gmail in the browser, then try again")
        fail("AUTH", "Google refused the address or the app password (%s)" % msg[:120].replace("\n", " "))
    return M, addr


def all_mail_box(M):
    """The 'All Mail' folder has a different name per Gmail language, but always carries the \\All flag."""
    typ, data = M.list()
    for raw in data or []:
        line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
        m = re.match(r'\((?P<flags>[^)]*)\)\s+(?:"[^"]*"|NIL)\s+(?P<name>.+)$', line)
        if m and "\\All" in m.group("flags"):
            return m.group("name").strip()
    return "INBOX"


def gmail_search(M, query):
    M.literal = query.encode("utf-8")
    typ, data = M.uid("SEARCH", "CHARSET", "UTF-8", "X-GM-RAW")
    if typ != "OK":
        fail("SEARCH", "Gmail search failed")
    return [int(x) for x in (data[0] or b"").split()]


def msgids(M, uids):
    """uid -> Gmail message id, in one round trip, so a rerun skips what it already has without downloading it."""
    out_map = {}
    for i in range(0, len(uids), 200):
        chunk = ",".join(str(u) for u in uids[i:i + 200])
        typ, data = M.uid("FETCH", chunk, "(X-GM-MSGID)")
        for row in data or []:
            line = row[0] if isinstance(row, tuple) else row
            if not isinstance(line, bytes):
                continue
            m_uid, m_id = re.search(rb"UID (\d+)", line), re.search(rb"X-GM-MSGID (\d+)", line)
            if m_uid and m_id:
                out_map[int(m_uid.group(1))] = m_id.group(1).decode()
    return out_map


def fetch_one(M, uid):
    typ, data = M.uid("FETCH", str(uid), "(X-GM-MSGID INTERNALDATE BODY.PEEK[])")
    if typ != "OK" or not data:
        return None, None, None
    for item in data:
        if isinstance(item, tuple):
            head = item[0].decode("utf-8", "replace")
            mid = re.search(r"X-GM-MSGID (\d+)", head)
            return (mid.group(1) if mid else "uid%d" % uid), imaplib.Internaldate2tuple(item[0]), item[1]
    return None, None, None


def public_https(url):
    """Only links to the public internet (many vendors' tracking links are plain http, so http stays allowed). An email is written by a stranger: a link to the router
    (http://192.168.1.1/...) or to this computer (localhost) would let that stranger act inside the owner's network."""
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname or u.hostname.endswith((".local", ".lan", ".internal", ".home")):
        return False
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global or ip.is_multicast:
            return False
    return bool(infos)


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not public_https(newurl):
            return None  # refused: urllib then raises, and the link counts as not downloaded
        return urllib.request.HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, headers, newurl)


def fetch_pdf_link(url, deadline_s=45):
    """GET a document link; keep it only if what comes back is really a PDF. Returns (bytes, filename, final_url) or None."""
    if not public_https(url):
        return None
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_ctx()), _CheckedRedirect())
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MAKERS receipts skill)"})
        stop = time.monotonic() + deadline_s
        with opener.open(req, timeout=20) as r:
            chunks, size = [], 0
            while size <= MAX_LINK_BYTES:
                if time.monotonic() > stop:
                    return None  # a server that drips forever never stalls the month
                b = r.read(64 * 1024)
                if not b:
                    break
                chunks.append(b)
                size += len(b)
            data = b"".join(chunks)
            final = r.geturl()
            disp = r.headers.get("Content-Disposition", "") or ""
    except Exception:
        return None
    if len(data) > MAX_LINK_BYTES or not data.startswith(b"%PDF-"):
        return None
    m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", disp, re.I)
    name = urllib.parse.unquote(m.group(1)) if m else os.path.basename(urllib.parse.urlparse(final).path)
    return data, name or "document.pdf", final


# ---------- parsing ----------

def safe_part(s, limit):
    s = unicodedata.normalize("NFC", str(s or ""))
    s = re.sub(r'[\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]', "", s)  # invisible direction marks
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s[:limit].strip(" .") or "x"


def sender_label(name, addr):
    name = (name or "").strip().strip('"')
    if name:
        return name
    dom = (addr or "").split("@")[-1]
    parts = [p for p in dom.split(".") if p not in ("com", "co", "il", "net", "org", "io", "ai", "mail", "email", "www")]
    return parts[0] if parts else (addr or "unknown")


def text_of(part):
    try:
        return part.get_content()
    except Exception:
        payload = part.get_payload(decode=True) or b""
        return payload.decode(part.get_content_charset() or "utf-8", "replace")


def bodies(msg):
    plain = html_body = ""
    try:
        p = msg.get_body(preferencelist=("plain",))
        if p is not None:
            plain = text_of(p)
        h = msg.get_body(preferencelist=("html",))
        if h is not None:
            html_body = text_of(h)
    except Exception:
        pass
    if not plain and html_body:
        plain = re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(style|script).*?</\1>", " ", html_body))
        plain = html.unescape(plain)
    return plain, html_body


def snippet(plain):
    keep = [l for l in plain.splitlines() if l.strip() and not SECRET_LINE.search(l)]
    s = re.sub(r"\s+", " ", " ".join(keep)).strip()
    s = CARD_NUM.sub("[מספר הוסתר]", s)
    if SECRET_LINE.search(plain) or re.search(r"קוד|\bcode\b", plain, re.I):
        s = re.sub(r"\b\d{4,8}\b", "[קוד הוסתר]", s)   # a one-time code often sits alone on its own line (morning, 2026)
    return s[:220]


def deep(url):
    """A link to a home page (no path, no query) is a logo or a footer, never a document."""
    u = urllib.parse.urlparse(url)
    return bool(u.query) or u.path.strip("/") != ""


def doc_links(plain, html_body):
    found = []
    for href, label in HREF.findall(html_body or ""):
        url = html.unescape(href).strip()
        text = html.unescape(re.sub(r"<[^>]+>", " ", label))
        if url.lower().startswith("http") and deep(url) and not SKIP_LINK.search(url + " " + text) and DOC_HINT.search(url + " " + text):
            found.append(url)
    for url in BARE_URL.findall(plain or ""):
        if deep(url) and not SKIP_LINK.search(url) and DOC_HINT.search(url):
            found.append(url)
    uniq = []
    for u in found:
        if u not in uniq:
            uniq.append(u)
    return uniq[:3]


def attachments(msg):
    """Receipt-like files: every PDF, and photos that were attached on purpose (not a 5 KB logo inside the email)."""
    files = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        name = part.get_filename() or ""
        low = name.lower()
        disp = part.get_content_disposition() or ""
        is_pdf = ctype == "application/pdf" or low.endswith(".pdf")
        is_photo = ctype in ("image/jpeg", "image/png", "image/heic") or low.endswith((".jpg", ".jpeg", ".png", ".heic"))
        if not (is_pdf or is_photo):
            continue
        data = part.get_payload(decode=True) or b""
        if is_pdf and len(data) < 1024:
            continue
        if is_photo and (disp != "attachment" or not name or len(data) < 30 * 1024):
            continue
        photo_ext = os.path.splitext(low)[1]
        if photo_ext not in (".jpg", ".jpeg", ".png", ".heic"):
            photo_ext = {"image/png": ".png", "image/heic": ".heic"}.get(ctype, ".jpg")  # never .command, .exe, .bat
        ext = ".pdf" if is_pdf else photo_ext
        files.append((name or "document" + ext, ext, data))
    return files


def message_date(msg, internal):
    try:
        d = parsedate_to_datetime(str(msg.get("date", "")))
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone().date()
    except Exception:
        pass
    if internal:
        return dt.date(internal.tm_year, internal.tm_mon, internal.tm_mday)
    return dt.date.today()


def gmail_link(addr, msg):
    mid = str(msg.get("message-id", "") or "").strip()
    if not mid:
        return ""
    q = urllib.parse.quote("rfc822msgid:" + mid.strip("<>"), safe="")
    return "https://mail.google.com/mail/?authuser=%s#search/%s" % (urllib.parse.quote(addr), q)


# ---------- the month folder ----------

def month_range(month):
    m = re.fullmatch(r"(\d{4})-(\d{2})", month or "")
    if not m or not 1 <= int(m.group(2)) <= 12:
        fail("MONTH", "month must look like 2026-09")
    y, mo = int(m.group(1)), int(m.group(2))
    start = dt.date(y, mo, 1)
    end = dt.date(y + (mo == 12), 1 if mo == 12 else mo + 1, 1)
    return start, end


def load_manifest(folder):
    try:
        with open(os.path.join(folder, MANIFEST), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"version": VERSION, "items": []}


def hide(path):
    """Dot files are hidden on a Mac already; on Windows they need the hidden attribute."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02)
        except Exception:
            pass


def save_manifest(folder, man):
    path = os.path.join(folder, MANIFEST)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    hide(path)


def unique_path(folder, base, ext, data):
    path = os.path.join(folder, base + ext)
    n = 2
    while os.path.exists(path):
        with open(path, "rb") as f:
            if hashlib.sha256(f.read()).hexdigest() == hashlib.sha256(data).hexdigest():
                return path, False
        path = os.path.join(folder, "%s (%d)%s" % (base, n, ext))
        n += 1
    return path, True


STATUS = {"file": "קובץ מצורף", "link": "הורד מקישור", "body": "המייל עצמו נשמר", "link_only": "בקישור, לא הורד", "none": "בלי מסמך"}
KINDS = {"receipt": ("קבלה", ""), "income": ("הכנסה, מסמך שהעסק שלכם הוציא", "הכנסות"), "not-receipt": ("לא קבלה", "לא קבלות")}


def cell(v):
    """A subject that starts with = + - or @ would run as a formula in Excel. Make it plain text."""
    v = str(v or "")
    head = re.sub(r"^[\s\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]+", "", v)[:1]
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") or head in ("=", "+", "-", "@") else v


def write_page(folder, rows):
    """The same list as a page, where every link is clickable and every file opens."""
    def a(href, text):
        return '<a href="%s">%s</a>' % (html.escape(href, quote=True), html.escape(text))
    trs = []
    for i in rows:
        files = "<br>".join(a(urllib.parse.quote(f), os.path.basename(f)) for f in i["files"])
        links = "<br>".join(a(u, "המסמך באתר של הספק") for u in i["links"]) if i["status"] == "link_only" else ""
        trs.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            html.escape(i["date"]), html.escape(i["from"]), html.escape(i["subject"]),
            html.escape(STATUS[i["status"]] + (", " + KINDS[i["kind"]][0] if i.get("kind") in KINDS and i["kind"] != "receipt" else "")),
            files, links, a(i["gmail"], "פתיחה") if i["gmail"] else ""))
    page = ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>קבלות %s</title>'
            '<style>body{font-family:system-ui,sans-serif;margin:24px}table{border-collapse:collapse;width:100%%}'
            'td,th{padding:6px 8px;border-bottom:1px solid #ddd;text-align:right;vertical-align:top;font-size:14px}</style>'
            '</head><body><h1>קבלות %s</h1><table><tr><th>תאריך</th><th>שולח</th><th>נושא</th><th>מה נמצא</th>'
            '<th>קבצים</th><th>מסמך שלא ירד</th><th>במייל</th></tr>%s</table></body></html>') % (
            html.escape(os.path.basename(folder)), html.escape(os.path.basename(folder)), "".join(trs))
    with open(os.path.join(folder, PAGE_NAME), "w", encoding="utf-8") as f:
        f.write(page)


def list_group(i):
    """Documents first, then links that did not download, income and not-receipts, and the emails with no document last.
    A real month (Daniel's September 2026) had 22 no-document rows out of 50; sorted by date only they buried the receipts."""
    if i.get("kind") == "income":
        return 2
    if i.get("kind") == "not-receipt":
        return 3
    if i["status"] == "none":
        return 4 if RECEIPT_SUBJECT.search(i.get("subject", "")) else 5   # a receipt that is the email itself, above the noise
    return {"file": 0, "link": 0, "body": 0, "link_only": 1}.get(i["status"], 5)


def write_list(folder, items):
    rows = sorted(items, key=lambda i: (list_group(i), i["date"], i["from"]))
    write_page(folder, rows)
    path = os.path.join(folder, LIST_NAME)
    header = ["תאריך", "שולח", "נושא", "מה נמצא", "סימון", "קבצים", "קישור למסמך", "פתיחה בג'ימייל"]

    def dump(p):
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            for i in rows:
                w.writerow([i["date"], cell(i["from"]), cell(i["subject"]), STATUS[i["status"]], KINDS.get(i.get("kind"), ("", ""))[0], " | ".join(i["files"]),
                            " | ".join(i["links"]), i["gmail"]])
    try:
        dump(path)
        return path
    except PermissionError:
        alt = os.path.join(folder, "רשימה (חדש).csv")
        dump(alt)
        out("WARNING LIST_LOCKED the list is open in another program (Excel?); wrote", alt)
        return alt


def process_message(msg, gm_id, internal, addr, folder, known_hashes, fetch_links):
    d = message_date(msg, internal)
    from_name, from_addr = parseaddr(str(msg.get("from", "")))
    who = sender_label(from_name, from_addr)
    subject = re.sub(r"\s+", " ", str(msg.get("subject", "") or "")).strip()
    plain, html_body = bodies(msg)
    item = {"id": gm_id, "date": d.isoformat(), "from": who, "from_addr": from_addr, "subject": subject,
            "snippet": snippet(plain), "status": "none", "files": [], "links": [], "gmail": gmail_link(addr, msg)}
    for name, ext, data in attachments(msg):
        h = hashlib.sha256(data).hexdigest()
        stem = os.path.splitext(name)[0]
        base = "%s_%s_%s" % (d.isoformat(), safe_part(who, 30), safe_part(stem, 40))
        if h in known_hashes:
            item["files"].append(known_hashes[h])
        else:
            path, new = unique_path(folder, base, ext, data)
            if new:
                with open(path, "wb") as f:
                    f.write(data)
            known_hashes[h] = os.path.basename(path)
            item["files"].append(os.path.basename(path))
        item["status"] = "file"
    links = doc_links(plain, html_body)
    item["links"] = links
    if item["status"] == "none" and links:
        item["status"] = "link_only"
        if fetch_links:
            for url in links:
                got = fetch_pdf_link(url)
                if not got:
                    continue
                data, name, _final = got
                h = hashlib.sha256(data).hexdigest()
                if h in known_hashes:
                    item["files"].append(known_hashes[h])
                else:
                    base = "%s_%s_%s" % (d.isoformat(), safe_part(who, 30), safe_part(os.path.splitext(name)[0], 40))
                    path, new = unique_path(folder, base, ".pdf", data)
                    if new:
                        with open(path, "wb") as f:
                            f.write(data)
                    known_hashes[h] = os.path.basename(path)
                    item["files"].append(os.path.basename(path))
                item["status"] = "link"
                break
    if item["status"] in ("none", "link_only"):
        # Many receipts are the email itself (app stores, rides, deliveries). Keep a copy aside;
        # the skill decides which ones are receipts and the keep command puts those into the month folder.
        bdir = os.path.join(folder, BODIES)
        os.makedirs(bdir, exist_ok=True)
        hide(bdir)
        page = html_body or "<pre>%s</pre>" % html.escape(plain)
        if "charset" not in page[:3000].lower():
            page = '<meta charset="utf-8">\n' + page
        page = NO_SCRIPT + page
        name = "%s.html" % safe_part(gm_id, 40)
        with open(os.path.join(bdir, name), "w", encoding="utf-8") as f:
            f.write(page)
        item["body"] = BODIES + "/" + name
    return item


# ---------- commands ----------

def cmd_status(_a):
    addr = read_email()
    if not addr:
        out("SETUP_NEEDED email")
        return
    prob = password_problem(read_password())
    if prob:
        out("SETUP_NEEDED password", prob, "email:", addr, "file:", PW_FILE)
        return
    out("READY", addr, "folder:", ROOT)


def cmd_setup(a):
    addr = (a.email or "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", addr):
        fail("EMAIL", "that does not look like an email address")
    private_write(EMAIL_FILE, addr + "\n")
    if a.password:
        private_write(PW_FILE, parse_password(a.password) + "\n")
        out("SAVED email and password. file:", PW_FILE)
        return
    if not os.path.exists(PW_FILE) or not read_password():
        private_write(PW_FILE, "")
    state = "HAS_PASSWORD" if read_password() else "EMPTY"
    opened = open_in_editor(PW_FILE)  # never empties a password that is already saved
    out("SAVED email", addr)
    out("PASSWORD_FILE", PW_FILE, "EDITOR_OPENED" if opened else "EDITOR_FAILED", state)


def cmd_check(_a):
    M, addr = login()
    box = all_mail_box(M)
    typ, _ = M.select(box, readonly=True)
    M.logout()
    if typ != "OK":
        fail("FOLDER", "logged in, but could not open the All Mail folder")
    out("OK", addr, "folder:", box)


def cmd_collect(a):
    start, end = month_range(a.month)
    folder = os.path.join(ROOT, a.month)
    os.makedirs(folder, exist_ok=True)
    M, addr = login()
    box = all_mail_box(M)
    typ, _ = M.select(box, readonly=True)  # EXAMINE: read only
    if typ != "OK":
        fail("FOLDER", "could not open the All Mail folder")
    # Gmail reads after:/before: dates as midnight Pacific time, so a receipt that arrived at 01:00 on the 1st
    # in Israel can fall into the previous month. Search one day wider on each side, then keep only the
    # emails whose local date is inside the month.
    query = "after:%s before:%s -in:sent -in:drafts -in:chats %s" % (
        (start - dt.timedelta(days=1)).strftime("%Y/%m/%d"), (end + dt.timedelta(days=1)).strftime("%Y/%m/%d"), KEYWORDS)
    uids = gmail_search(M, query)
    man = load_manifest(folder)
    seen = {i["id"] for i in man["items"]}
    known = {}
    for base, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in names:
            if name.startswith(".") or name.endswith(".csv") or name == PAGE_NAME:
                continue
            p = os.path.join(base, name)
            with open(p, "rb") as f:
                known[hashlib.sha256(f.read()).hexdigest()] = os.path.relpath(p, folder).replace(os.sep, "/")
    ids = msgids(M, uids)
    uids = [u for u in uids if ids.get(u) not in seen]
    if len(uids) > a.max:
        out("WARNING TOO_MANY", len(uids), "new matching emails; reading the newest", a.max, "now, the rest on the next run")
        uids = uids[-a.max:]
    out("MATCHED", len(uids), "new emails in", a.month, "(reading now; about one second each)")
    new = 0
    for n, uid in enumerate(uids, 1):
        if ids.get(uid) in seen:
            continue
        gm_id, internal, raw = fetch_one(M, uid)
        if raw is None or gm_id in seen:
            continue
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        if not start <= message_date(msg, internal) < end:
            continue  # the extra day on either side belongs to the neighbouring month
        try:
            item = process_message(msg, gm_id, internal, addr, folder, known, not a.no_links)
        except Exception as e:  # one strange email never stops the month
            out("WARNING UNREADABLE one email could not be read (%s); it is listed without a file" % e.__class__.__name__)
            item = {"id": gm_id, "date": start.isoformat(), "from": "?", "from_addr": "", "subject": "(could not read: %s)" % e.__class__.__name__,
                    "snippet": "", "status": "none", "files": [], "links": [], "gmail": ""}
        man["items"].append(item)
        seen.add(gm_id)
        new += 1
        if n % 20 == 0:
            out("progress", n, "/", len(uids))
            save_manifest(folder, man)
    try:
        M.logout()
    except Exception:
        pass
    man["month"], man["updated"] = a.month, dt.datetime.now().isoformat(timespec="seconds")
    save_manifest(folder, man)
    report(folder, man, new)


def report(folder, man, new=None):
    items = man["items"]
    lst = write_list(folder, items)
    c = {k: sum(1 for i in items if i["status"] == k) for k in STATUS}
    files = len({f for i in items for f in i["files"]})
    out("MONTH", man.get("month", os.path.basename(folder)))
    out("FOLDER", folder)
    out("EMAILS", len(items), "" if new is None else "(new this run: %d)" % new)
    out("FILES", files)
    out("WITH_ATTACHMENT", c["file"], "| DOWNLOADED_FROM_LINK", c["link"], "| EMAIL_KEPT", c["body"], "| LINK_ONLY", c["link_only"], "| NO_DOCUMENT", c["none"])
    out("LIST", lst)
    out("PAGE", os.path.join(folder, PAGE_NAME))
    out("DETAILS", os.path.join(folder, MANIFEST))
    if not items:
        out("NOTE zero matching emails is a normal result for a quiet month or a new mailbox")
    out("DONE")


def find_item(man, item_id, folder):
    for item in man["items"]:
        if item["id"] == item_id:
            return item
    fail("NOT_FOUND", "no email with id %s in %s" % (item_id, folder))


def cmd_summary(a):
    """The same closing lines as collect, from what is already on disk. No network."""
    month_range(a.month)
    folder = os.path.join(ROOT, a.month)
    if not os.path.exists(os.path.join(folder, MANIFEST)):
        fail("NOT_COLLECTED", "this month was not collected yet")
    report(folder, load_manifest(folder))


def cmd_mark(a):
    """The owner decided what an email's files are. income and not-receipt move them into a subfolder; receipt moves them back."""
    folder = os.path.join(ROOT, a.month)
    man = load_manifest(folder)
    item = find_item(man, a.id, folder)
    label, sub = KINDS[a.kind]
    files, moved = [], {}
    for f in item["files"]:
        dst_rel = (sub + "/" if sub else "") + os.path.basename(f)
        src, dst = os.path.join(folder, f), os.path.join(folder, dst_rel)
        if os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            stem, ext = os.path.splitext(os.path.basename(f))
            n = 2
            while os.path.exists(dst):  # another document already has this name there: never overwrite it
                dst_rel = (sub + "/" if sub else "") + "%s (%d)%s" % (stem, n, ext)
                dst = os.path.join(folder, dst_rel)
                n += 1
            os.rename(src, dst)
        files.append(dst_rel)
        moved[f] = dst_rel
    item["files"], item["kind"] = files, a.kind
    for other in man["items"]:  # a duplicate email points at the same file
        if other is not item:
            other["files"] = [moved.get(f, f) for f in other["files"]]
    save_manifest(folder, man)
    write_list(folder, man["items"])
    out("MARKED", a.id, "as", label, ("moved to " + sub) if (sub and files) else "")


def cmd_keep(a):
    """Save the email itself as the document, for receipts that have no file and no link."""
    folder = os.path.join(ROOT, a.month)
    man = load_manifest(folder)
    item = find_item(man, a.id, folder)
    if not item.get("body") or not os.path.exists(os.path.join(folder, item["body"])):
        fail("NO_BODY", "there is no saved copy of this email")
    with open(os.path.join(folder, item["body"]), "rb") as f:
        data = f.read()
    base = "%s_%s_%s" % (item["date"], safe_part(item["from"], 30), safe_part(item["subject"], 40))
    path, new = unique_path(folder, base, ".html", data)
    if new:
        with open(path, "wb") as f:
            f.write(data)
    item["files"], item["status"], item["kind"] = [os.path.basename(path)], "body", "receipt"
    save_manifest(folder, man)
    write_list(folder, man["items"])
    out("KEPT", a.id, "as", os.path.basename(path))


def cmd_open(a):
    path = os.path.join(ROOT, a.month) if a.month else ROOT
    os.makedirs(path, exist_ok=True)
    out("OPENED" if open_folder(path) else "NOT_OPENED", path)


def cmd_selftest(_a):
    from email.message import EmailMessage
    assert sys.version_info >= (3, 8), "Python 3.8 or newer is needed"
    m = EmailMessage()
    m["From"] = '"חברת הדוגמה בע״מ" <billing@example.co.il>'
    m["Subject"] = "קבלה מספר 1234"
    m["Date"] = "Mon, 14 Sep 2026 10:00:00 +0300"
    m["Message-ID"] = "<abc@example.co.il>"
    m.set_content("תודה על התשלום.\nהסיסמה שלך: 1234\nכרטיס 4580 1234 5678 9012\n")
    m.add_alternative('<p>תודה</p><a href="https://example.co.il/docs/invoice-1234.pdf">להורדת החשבונית</a>'
                      '<a href="https://example.co.il/unsubscribe">הסרה מרשימת התפוצה</a>', subtype="html")
    m.add_attachment(b"%PDF-1.4\n" + b"0" * 2048, maintype="application", subtype="pdf", filename="Receipt-1234.pdf")
    m.add_attachment(b"\x89PNG" + b"0" * 900, maintype="image", subtype="png", filename="logo.png")
    msg = email.message_from_bytes(m.as_bytes(), policy=email.policy.default)
    atts = attachments(msg)
    assert [a[0] for a in atts] == ["Receipt-1234.pdf"], atts
    plain, h = bodies(msg)
    assert doc_links(plain, h) == ["https://example.co.il/docs/invoice-1234.pdf"], doc_links(plain, h)
    assert doc_links("", '<a href="https://link.apple.com/account/toggle-renewal-receipts/x">Turn Off Renewal Receipt Emails</a>'
                     '<a href="https://help.bird.co/receipts">receipt help</a>') == []
    assert doc_links("", '<a href="https://www.greeninvoice.co.il/api/v1/documents/download?d=1">להורדת המסמך</a>')
    assert "4821" not in snippet("שלום\nהנה קוד האימות שלך: 4821\nהקוד החד פעמי בתוקף")
    assert "482193" not in snippet("את הקוד מזינים בחלונית שנפתחה\n482193\nנפגש במערכת")
    sn = snippet(plain)
    assert "1234\n" not in sn and "הסיסמה" not in sn and "5678" not in sn, sn
    assert safe_part('a/b:c*?"<>|d.', 30) == "a b c d", safe_part('a/b:c*?"<>|d.', 30)
    assert safe_part("\u200fוולט\u200e", 30) == "וולט"
    assert parse_password("abcd efgh ijkl mnop\n") == "abcdefghijklmnop"
    assert password_problem("abcdefghijklmnop") == "" and password_problem("short")
    assert month_range("2026-12") == (dt.date(2026, 12, 1), dt.date(2027, 1, 1))
    with tempfile.TemporaryDirectory() as t:
        item = process_message(msg, "1", None, "me@gmail.com", t, {}, False)
        assert item["status"] == "file" and item["files"] == ["2026-09-14_חברת הדוגמה בע״מ_Receipt-1234.pdf"], item
        known = {hashlib.sha256(atts[0][2]).hexdigest(): item["files"][0]}
        again = process_message(msg, "2", None, "me@gmail.com", t, known, False)
        assert again["files"] == item["files"] and len(os.listdir(t)) == 1
        p = write_list(t, [item])
        with open(p, encoding="utf-8-sig") as f:
            assert "קובץ מצורף" in f.read()
        noise = dict(item, id="3", date="2026-09-01", status="none", files=[])
        p = write_list(t, [noise, item])
        with open(p, encoding="utf-8-sig") as f:
            body = f.read()
        assert body.index("קובץ מצורף") < body.index("בלי מסמך"), "documents come before the no-document rows"
        assert not deep("https://www.greeninvoice.co.il") and deep("https://x.co.il/api/download?d=1")
    assert "rfc822msgid" in gmail_link("me@gmail.com", msg)
    assert cell("=HYPERLINK(1)") == "'=HYPERLINK(1)" and cell("קבלה") == "קבלה"
    assert cell("\t=1") == "'\t=1" and cell("\u200f=1") == "'\u200f=1"
    assert not public_https("http://192.168.1.1/apply.cgi?x=1") and not public_https("https://127.0.0.1/a")
    assert not public_https("https://localhost/a") and not public_https("ftp://example.com/a.pdf")
    assert doc_links("", '<a href="https://shop.example/magic?t=1">Sign in to view your invoice</a>') == []
    if sys.platform == "darwin" or sys.platform.startswith("win"):
        # without root certificates the first real run fails on the secure connection; catch it here, offline
        if not ssl_ctx().cert_store_stats().get("x509_ca"):
            out("SELFTEST FAILED SSL no root certificates; on a Mac with Python from python.org run Install Certificates.command once")
            sys.exit(3)
    out("SELFTEST OK", "python", sys.version.split()[0], "settings:", SETTINGS, "folder:", ROOT)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Collect receipts and invoices from Gmail into a folder per month (read only).")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("status")
    s = sub.add_parser("setup")
    s.add_argument("--email", required=True)
    s.add_argument("--password")
    sub.add_parser("check")
    c = sub.add_parser("collect")
    c.add_argument("--month", required=True)
    c.add_argument("--no-links", action="store_true", help="do not try to download documents from links")
    c.add_argument("--max", type=int, default=300)
    k = sub.add_parser("mark")
    k.add_argument("--month", required=True)
    k.add_argument("--id", required=True)
    k.add_argument("--as", dest="kind", required=True, choices=sorted(KINDS))
    sm = sub.add_parser("summary")
    sm.add_argument("--month", required=True)
    kp = sub.add_parser("keep")
    kp.add_argument("--month", required=True)
    kp.add_argument("--id", required=True)
    o = sub.add_parser("open")
    o.add_argument("--month")
    sub.add_parser("selftest")
    a = ap.parse_args()
    fn = {"status": cmd_status, "setup": cmd_setup, "check": cmd_check, "collect": cmd_collect,
          "mark": cmd_mark, "keep": cmd_keep, "summary": cmd_summary, "open": cmd_open, "selftest": cmd_selftest}.get(a.cmd)
    if not fn:
        ap.print_help()
        sys.exit(1)
    fn(a)


if __name__ == "__main__":
    main()
