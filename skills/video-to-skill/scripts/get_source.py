#!/usr/bin/env python3
"""Gets the words of a source into one text file with times, so a skill can be built from it.

Usage:  bash run.sh get_source.py SOURCE --work FOLDER [--lang he|en|auto] [--start M:SS] [--end M:SS] [--frames]

SOURCE is one of:
  a YouTube link       captions first (seconds, nothing downloads); no captions: the sound downloads and is
                       transcribed on this computer
  a video link         Instagram, TikTok, Facebook, Vimeo, X: the video downloads and is transcribed here
  an article link      the text of the page
  a file               a video or a recording (transcribed here), or text: .txt .md .srt .vtt .html

Writes into FOLDER:
  source.txt           a short header, then the words, one line per piece with its time: [1:05] ...
  meta.json            title, kind, how the words were read, language, length
  video.mp4            only with --frames, for a link; a local video file is used where it is
and prints, last, one line:  SOURCE READY <path to source.txt> · <n> words · <how>
or a line starting PROBLEM that says what to do. Run it in the background and wait for SOURCE READY:
transcribing a long video takes minutes.

Only the standard library is needed for an article or a text file, so the Claude app can run it with python3.
"""
import html, json, os, re, subprocess, sys, urllib.request
from html.parser import HTMLParser
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mp3", ".m4a", ".wav", ".aac", ".ogg", ".opus", ".flac"}
TEXT_EXT = {".txt", ".md", ".srt", ".vtt", ".html", ".htm"}
VIDEO_HOSTS = ("instagram.com", "tiktok.com", "facebook.com", "fb.watch", "vimeo.com", "x.com", "twitter.com",
               "threads.net", "linkedin.com/posts", "dailymotion.com", "loom.com")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def say(msg):
    print(msg, flush=True)


def die(msg):
    say("PROBLEM " + msg)
    sys.exit(1)


def secs(v):
    if v is None:
        return None
    p = [float(x) for x in str(v).split(":")]
    return sum(x * 60 ** i for i, x in enumerate(reversed(p)))


def stamp(sec):
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def has_hebrew(t):
    return len(re.findall(r"[֐-׿]", t)) > len(re.findall(r"[A-Za-z]", t)) * 0.3


# ---------- captions and subtitles ----------

def parse_vtt(text):
    """(seconds, line) from VTT or SRT, with YouTube's rolling captions folded so each line appears once."""
    out, last, t = [], None, 0.0
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        lines = block.strip().split("\n")
        tl = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if tl is None:
            continue
        m = re.match(r"\s*(\d+:)?(\d+):(\d+)[.,](\d+)", lines[tl])
        if m:
            t = int((m.group(1) or "0:")[:-1]) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        for raw in lines[tl + 1:]:
            s = html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()
            s = re.sub(r"\s+", " ", s)
            if not s or s == last:
                continue
            out.append((t, s))
            last = s
    return out


def paragraphs(lines, gap=20):
    """Joins short caption lines into pieces of about `gap` seconds, each with the time it starts."""
    out, cur, t0 = [], [], None
    for t, s in lines:
        if t0 is None:
            t0 = t
        cur.append(s)
        if t - t0 >= gap or s.endswith((".", "?", "!")) and t - t0 >= gap / 2:
            out.append((t0, " ".join(cur)))
            cur, t0 = [], None
    if cur:
        out.append((t0, " ".join(cur)))
    return out


# ---------- links ----------

def ytdlp(args, timeout=600):
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        die("reading a video link needs the tools on this computer (install-tools.sh base). In the Claude app: "
            "ask the owner to paste the transcript (on YouTube: the three dots under the video, Show transcript).")
    r = subprocess.run([sys.executable, "-m", "yt_dlp", "--no-warnings", "--no-playlist", *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def ytdlp_problem(err, url):
    e = err.lower()
    if "login" in e or "rate-limit" in e or "cookies" in e or "private" in e or "not available" in e:
        die("the site does not let this video be read from a link (it asks for a login, or it is private). "
            "Ask the owner to save the video to the computer (or to screen-record it) and give you the file. "
            "Do not ask for their password.")
    if "unsupported url" in e:
        return None
    die("the video did not download. Run install-tools.sh update once (sites change and yt-dlp follows them) "
        "and try again. If it fails again, ask the owner for the file. Details: " + err.strip().splitlines()[-1][:200]
        if err.strip() else "the video did not download.")


def video_info(url):
    code, out, err = ytdlp(["--skip-download", "--dump-single-json", url], timeout=120)
    if code != 0:
        ytdlp_problem(err, url)
        return None
    try:
        return json.loads(out)
    except ValueError:
        return None


def youtube_captions(url, info, lang, work):
    """Manual captions first, then automatic ones, in the video's own language when known."""
    vlang = (info.get("language") or "").split("-")[0]
    pref = [x for x in (lang, vlang, "he", "iw", "en") if x and x != "auto"]
    pref = list(dict.fromkeys(pref))
    subs, auto = info.get("subtitles") or {}, info.get("automatic_captions") or {}

    def find(pool, orig_only=False):
        for p in pref:
            for k in pool:
                base = k.split("-")[0]
                if base == p and (not orig_only or k.endswith("-orig") or k == vlang):
                    return k
        return None

    key, kind = find(subs), "captions"
    if not key:
        key, kind = (find(auto, orig_only=True) or find(auto)), "automatic captions"
    if not key:
        return None, None
    tmp = work / "captions"
    tmp.mkdir(exist_ok=True)
    flag = "--write-subs" if kind == "captions" else "--write-auto-subs"
    code, _o, err = ytdlp(["--skip-download", flag, "--sub-langs", key, "--sub-format", "vtt",
                           "-o", str(tmp / "c.%(ext)s"), url], timeout=120)
    f = next(iter(sorted(tmp.glob("*.vtt"))), None)
    if not f:
        return None, None
    return parse_vtt(f.read_text(encoding="utf-8", errors="replace")), f"{kind} ({key})"


def download(url, work, audio_only):
    fmt = "ba[ext=m4a]/ba/b" if audio_only else "b[height<=720][ext=mp4]/b[height<=720]/b/bv*[height<=720]"
    name = "audio" if audio_only else "video"
    code, _o, err = ytdlp(["-f", fmt, "-o", str(work / (name + ".%(ext)s")), url], timeout=1800)
    got = sorted(work.glob(name + ".*"))
    if code != 0 or not got:
        ytdlp_problem(err, url)
        die("the video did not download.")
    return got[0]


def video_only_for_frames(url, work):
    code, _o, err = ytdlp(["-f", "bv*[height<=480][ext=mp4]/bv*[height<=480]/b[height<=480]/b",
                           "-o", str(work / "video.%(ext)s"), url], timeout=1800)
    got = sorted(work.glob("video.*"))
    return got[0] if code == 0 and got else None


class TextOfPage(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "footer", "header", "aside", "form", "svg", "button", "template"}
    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "pre", "blockquote", "td", "figcaption", "dt", "dd"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip, self.cur, self.out, self.title, self.tag, self.in_title = 0, [], [], "", None, False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag == "title":
            self.in_title = True
        if tag in self.BLOCK:
            self.flush()
            self.tag = tag
        if tag == "br":
            self.cur.append(" ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag == "title":
            self.in_title = False
        if tag in self.BLOCK:
            self.flush()

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif not self.skip:
            self.cur.append(data)

    def flush(self):
        s = re.sub(r"\s+", " ", "".join(self.cur)).strip()
        if s:
            mark = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "### ", "li": "• "}.get(self.tag, "")
            self.out.append(mark + s)
        self.cur, self.tag = [], None


def article(url):
    import ssl
    ctx = None
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
    try:
        class Follow308(urllib.request.HTTPRedirectHandler):
            # Python before 3.11 does not follow 308, and sites move pages with it
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return super().redirect_request(req, fp, 307 if code == 308 else code, msg, headers, newurl)

            def http_error_308(self, req, fp, code, msg, headers):
                return self.http_error_302(req, fp, code, msg, headers)
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx), Follow308)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "he,en;q=0.8"})
        with opener.open(req, timeout=40) as r:
            raw, ctype = r.read(), r.headers.get("Content-Type", "")
    except Exception as e:
        die(f"the page did not open ({type(e).__name__}: {str(e)[:120]}). Ask the owner to copy the text of "
            "the article and paste it, or to save the page as a file. Do not read the link with a web or search "
            "tool instead: it returns a summary, not the article.")
    if "pdf" in ctype:
        die("this link is a PDF. Download it and read it with your own file reader, then save its text as a "
            ".txt file and run this again on that file.")
    m = re.search(r"charset=([\w-]+)", ctype) or re.search(r"charset=[\"']?([\w-]+)", raw[:3000].decode("ascii", "ignore"))
    enc = m.group(1) if m else "utf-8"
    try:
        text = raw.decode(enc, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")
    p = TextOfPage()
    p.feed(text)
    p.flush()
    # keep the longest run of real paragraphs: menus and link lists are short lines
    lines, seen = [], set()
    for l in p.out:
        if not (len(l.split()) >= 4 or l.startswith("#")) or (len(l) > 30 and l in seen):
            continue  # menus are short lines, and some pages print the same block twice
        seen.add(l)
        lines.append(l)
    return html.unescape(p.title).strip(), lines


# ---------- main ----------

def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return

    def opt(name, default=None):
        if name in a:
            i = a.index(name)
            if i + 1 >= len(a):
                die(f"{name} needs a value")
            return a[i + 1]
        return default

    src = a[0].strip()
    work = Path(opt("--work", "video-to-skill-work")).expanduser()
    work.mkdir(parents=True, exist_ok=True)
    lang = opt("--lang", "auto")
    start, end = secs(opt("--start")), secs(opt("--end"))
    frames = "--frames" in a
    meta = {"source": src, "title": "", "kind": "", "how": "", "lang": lang, "seconds": None, "video": None}
    pieces = None

    if re.match(r"https?://", src):
        low = src.lower()
        if "youtube.com" in low or "youtu.be" in low:
            info = video_info(src) or {}
            meta.update(kind="youtube", title=info.get("title", ""), seconds=info.get("duration"),
                        channel=info.get("channel") or info.get("uploader"))
            lines, how = youtube_captions(src, info, lang, work)
            if lines:
                meta["how"] = how
                if start is not None or end is not None:
                    lines = [(t, s) for t, s in lines if (start or 0) <= t <= (end or 1e9)]
                pieces = paragraphs(lines)
            else:
                say("no captions on this video, so the sound is transcribed here, on this computer")
                audio = download(src, work, audio_only=True)
                pieces = transcribe_here(audio, lang, start, end, meta)
            if frames:
                say("downloading the picture of the video for the frames (a small copy, no sound)")
                v = video_only_for_frames(src, work)
                meta["video"] = str(v) if v else None
                if not v:
                    say("the picture did not download, so there is no screen read for this video. Continue with the words.")
        elif any(h in low for h in VIDEO_HOSTS):
            meta["kind"] = "video link"
            info = video_info(src) or {}
            meta.update(title=info.get("title") or info.get("description", "")[:80], seconds=info.get("duration"))
            v = download(src, work, audio_only=False)
            meta["video"] = str(v)
            pieces = transcribe_here(v, lang, start, end, meta)
        else:
            title, lines = article(src)
            words = sum(len(l.split()) for l in lines)
            if words < 150:
                die("the page has almost no text that can be read from a link (it is closed, or built by scripts). "
                    "Ask the owner to copy the article text and paste it. Do not read it with a web or search tool "
                    "instead: it returns a summary, not the article.")
            meta.update(kind="article", title=title, how="page text")
            pieces = [(None, l) for l in lines]
    else:
        f = Path(src).expanduser()
        if not f.is_file():
            die(f"no file at {f}. Ask for the full path, in double quotes.")
        ext = f.suffix.lower()
        meta["title"] = f.stem
        if ext in VIDEO_EXT:
            meta.update(kind="file", video=str(f) if ext not in {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".opus", ".flac"} else None)
            pieces = transcribe_here(f, lang, start, end, meta)
        elif ext in {".srt", ".vtt"}:
            meta.update(kind="subtitles file", how="subtitles")
            pieces = paragraphs(parse_vtt(f.read_text(encoding="utf-8", errors="replace")))
        elif ext in {".html", ".htm"}:
            p = TextOfPage()
            p.feed(f.read_text(encoding="utf-8", errors="replace"))
            p.flush()
            meta.update(kind="page file", how="page text", title=p.title.strip() or f.stem)
            pieces = [(None, l) for l in p.out]
        elif ext in TEXT_EXT:
            meta.update(kind="text file", how="text")
            pieces = [(None, l.strip()) for l in f.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
        else:
            die(f"a {ext} file is not something this script reads. A PDF or Word file: read it with your own "
                "file reader and save its text as a .txt file, then run this again on the .txt file.")

    body = "".join((f"[{stamp(t)}] {s}\n" if t is not None else f"{s}\n") for t, s in pieces)
    words = len(body.split())
    sample = body[:4000]
    if meta["lang"] in (None, "auto"):
        meta["lang"] = "he" if has_hebrew(sample) else "en"
    meta["words"] = words
    head = f"# {meta['title'] or 'source'}\n# from: {src}\n# read as: {meta['how']}\n\n"
    out = work / "source.txt"
    out.write_text(head + body, encoding="utf-8")
    (work / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if words > 12000:
        say(f"LONG this source has {words} words. Read it in parts, or ask the owner which part matters.")
    say(f"SOURCE READY {out} · {words} words · {meta['how']}")


def transcribe_here(path, lang, start, end, meta):
    sys.path.insert(0, str(HERE))
    import transcribe as T
    if not T.libs_ok():
        die("NEEDS LIBS the transcription libraries are not installed yet. Run install-tools.sh libs (a few "
            "minutes, once), then run this again.")
    if lang in (None, "auto"):
        lang = guess_lang(meta)
    lines = T.transcribe(path, None if lang == "auto" else lang, None, start or 0.0, end)
    meta["how"] = f"transcribed on this computer ({T.pick_model(lang)} model, {lang})"
    meta["lang"] = lang
    return paragraphs(lines, gap=15)


def guess_lang(meta):
    # Hebrew first: only a title with several English words and no Hebrew at all counts as English
    t = (meta.get("title") or "") + " " + (meta.get("channel") or "")
    if re.search("[֐-׿]", t):
        return "he"
    if len(re.findall(r"[A-Za-z]{3,}", t)) >= 4:
        return "en"
    return "he"


if __name__ == "__main__":
    main()
