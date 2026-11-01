# -*- coding: utf-8 -*-
"""music_bed.py: a song without the vocals under a talking video, with the music ducking by itself.

A free skill by MAKERS (themakers.co.il). Runs the same on Mac and Windows.

    PY music_bed.py selftest              checks the tool itself, no internet, nothing installed
    PY music_bed.py setup                 installs everything once into ~/.music-bed-skill (long, see below)
    PY music_bed.py status                READY or SETUP_NEEDED, and the songs already saved
    PY music_bed.py get "<song or link>"  downloads one song (yt-dlp)
    PY music_bed.py split "<song>"        removes the vocals (Demucs, on this computer) and runs the check
    PY music_bed.py mix "<video>" "<song>" [--start SEC] [--use auto|instrumental|original] [--level DB]
    PY music_bed.py open                  opens the output folder
    PY music_bed.py update                refreshes the downloader when YouTube changed something

Everything this tool installs lives in ~/.music-bed-skill. Everything it makes lives in ~/מוזיקה לריל.
Delete both folders and it is gone. It never touches the original video or song file.

Every line the agent needs to read starts with an English word in capitals (READY, SAVED, VERDICT...).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

VERSION = "1.0.0"
WIN = os.name == "nt"
HOME = Path.home()
TOOL = HOME / ".music-bed-skill"
OUT = HOME / "מוזיקה לריל"
SONGS = OUT / "שירים"
BOOT = TOOL / "boot"
ENV = TOOL / "env"
LOG = TOOL / "setup.log"
READY_FILE = TOOL / "ready.json"
LAST_FILE = TOOL / "last-song.json"   # so the agent can say "last" and never has to echo a Hebrew path back
PY_VERSION = "3.12"
PACKAGES = ["demucs==4.1.0", "numpy", "yt-dlp[default]", "imageio-ffmpeg", "deno"]

# The proven bed recipe (desert series, 29.10.2026): bed at about -22.4 LUFS over the window it plays,
# ducked by the voice, 0.15 s fade in, 1 s fade out, limiter at 0.89. Final reels landed at -14.4/-15.0 LUFS.
BED_LUFS = -22.4
SOLO_LUFS = -16.0   # a video with no voice at all: the music is the sound, at a normal listening level
REF_VOICE_LUFS = -15.0   # the voice of those reels (master.mp4 measured -15.0)
FADE_IN = 0.15
FADE_OUT = 1.0
DUCK = "sidechaincompress=threshold=0.03:ratio=5:attack=15:release=350:makeup=1"

# The built-in check, from nine real songs (29.10.2026). Mean volume, dB.
NO_VOCALS_STEM = -50.0    # Soulful Strut -75.8, Green Onions -60.3: no singing at all
ALMOST_INSTR_GAP = 18.0   # Veridis Quo 18.6, Every Living Breathing Moment 21.3: Demucs may eat the lead synth
HEAVY_GAP = 7.5           # Touch The Sky 7.0, False Prophets 4.9: dense vocals, listen for residue

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg", ".opus", ".webm", ".mp4"}


def _utf8_console():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def say(*parts):
    print(*parts, flush=True)


# ---------------------------------------------------------------- pure helpers (selftest covers these)

def slugify(text):
    t = text
    t = re.sub(r"[\(\[][^\)\]]*(official|audio|video|lyric|lyrics|visualizer|remaster|hd|hq|4k|mv|clip)[^\)\]]*[\)\]]", " ", t, flags=re.I)
    t = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", t)
    t = re.sub(r"[^\w\s\-']", " ", t, flags=re.U)
    t = t.replace("'", "")
    t = re.sub(r"[\s_\-]+", "-", t.strip()).strip("-").lower()
    t = t[:50].strip("-")
    return t or "song"


def verdict(mix_mean, vocal_mean):
    """Return (code, gap). code: NO_VOCALS, ALMOST_INSTRUMENTAL, HEAVY_VOCALS or OK."""
    gap = round(mix_mean - vocal_mean, 1)
    if vocal_mean <= NO_VOCALS_STEM:
        return "NO_VOCALS", gap
    if gap >= ALMOST_INSTR_GAP:
        return "ALMOST_INSTRUMENTAL", gap
    if gap < HEAVY_GAP:
        return "HEAVY_VOCALS", gap
    return "OK", gap


def auto_use(code):
    return "original" if code in ("NO_VOCALS", "ALMOST_INSTRUMENTAL") else "instrumental"


def parse_duration(ffmpeg_info):
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", ffmpeg_info)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def parse_streams(ffmpeg_info):
    has_audio = re.search(r"Stream #\S+.*?: Audio:", ffmpeg_info) is not None
    m = re.search(r"Stream #\S+.*?: Video: (\w+)", ffmpeg_info)
    return has_audio, (m.group(1) if m else None)


def parse_lufs(ebur_out):
    vals = re.findall(r"^\s+I:\s+(-?[\d.]+|-inf)\s+LUFS", ebur_out, flags=re.M)
    if not vals:
        return None
    v = vals[-1]
    return -70.0 if v == "-inf" else float(v)


def parse_mean(volumedetect_out):
    m = re.findall(r"mean_volume:\s*(-?[\d.]+|-inf) dB", volumedetect_out)
    if not m:
        return None
    return -91.0 if m[-1] == "-inf" else float(m[-1])


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def plan_levels(bed_lufs, voice_lufs, level=0.0):
    """Bed gain and voice key gain, in dB. With a voice at the reference level this is exactly the proven recipe."""
    key = 0.0
    if voice_lufs is None or voice_lufs <= -60:
        target = SOLO_LUFS + level
    else:
        target = BED_LUFS + level
        if voice_lufs < REF_VOICE_LUFS:
            target += voice_lufs - REF_VOICE_LUFS   # a quieter voice gets a quieter bed, same balance
        key = clamp(REF_VOICE_LUFS - voice_lufs, -10.0, 20.0)  # so the duck reacts to this voice like to ours
    if bed_lufs is None or bed_lufs <= -60:
        gain = 0.0
    else:
        gain = clamp(target - bed_lufs, -30.0, 20.0)
    return round(gain, 2), round(key, 2), round(target, 2)


def build_filter(dur, gain, key, has_voice):
    fs = max(0.0, round(dur - FADE_OUT, 3))
    fmt = "aformat=sample_rates=48000:channel_layouts=stereo"
    bed = "[1:a]atrim=0:%s,asetpts=PTS-STARTPTS,%s,volume=%sdB,afade=t=in:d=%s" % (dur, fmt, gain, FADE_IN)
    if not has_voice:
        return "%s,afade=t=out:st=%s:d=%s,apad=whole_dur=%s,atrim=0:%s,alimiter=limit=0.89:level=false[a]" % (
            bed, fs, FADE_OUT, dur, dur)
    return (
        "[0:a]%s,asplit=2[v1][v2];"
        "[v1]apad=whole_dur=%s,atrim=0:%s,volume=%sdB[sc];"
        "%s[m];"
        "[m][sc]%s[md];"
        "[md]afade=t=out:st=%s:d=%s[mf];"
        "[v2]apad=whole_dur=%s,atrim=0:%s[vv];"
        "[vv][mf]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.89:level=false[a]"
    ) % (fmt, dur, dur, key, bed, DUCK, fs, FADE_OUT, dur, dur)


def out_name(video, slug):
    base = OUT / ("%s עם %s.mp4" % (Path(video).stem, slug))
    n = 2
    while base.exists():
        base = OUT / ("%s עם %s (%d).mp4" % (Path(video).stem, slug, n))
        n += 1
    return base


# ---------------------------------------------------------------- environment

def vbin(venv):
    return venv / ("Scripts" if WIN else "bin")


def vpy(venv):
    return vbin(venv) / ("python.exe" if WIN else "python")


def child_env():
    e = os.environ.copy()
    e["PATH"] = str(vbin(ENV)) + os.pathsep + str(vbin(BOOT)) + os.pathsep + e.get("PATH", "")
    e["HF_HOME"] = str(TOOL / "models")
    e["TORCH_HOME"] = str(TOOL / "models" / "torch")   # the fallback model download stays inside the tool folder too
    e["HF_HUB_DISABLE_TELEMETRY"] = "1"
    e["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    e["UV_CACHE_DIR"] = str(TOOL / "cache")
    e["UV_PYTHON_INSTALL_DIR"] = str(TOOL / "python")
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    e["MUSIC_BED_IN_ENV"] = "1"
    if READY_FILE.exists():
        e["HF_HUB_OFFLINE"] = "1"   # the model is already on this computer; no network, no token warning
    return e


def ready():
    return READY_FILE.exists() and vpy(ENV).exists()


def in_env():
    try:
        return Path(sys.prefix).resolve() == ENV.resolve()
    except OSError:
        return False


def ffmpeg():
    import imageio_ffmpeg  # only inside the env
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def probe(path):
    r = run([ffmpeg(), "-hide_banner", "-i", path])
    return r.stderr


def lufs(path, start=0.0, dur=None):
    cmd = [ffmpeg(), "-nostats", "-hide_banner"]
    if start:
        cmd += ["-ss", "%.3f" % start]
    if dur:
        cmd += ["-t", "%.3f" % dur]
    cmd += ["-i", path, "-map", "0:a:0", "-af", "ebur128", "-f", "null", "-"]
    return parse_lufs(run(cmd).stderr)


def mean_volume(path):
    r = run([ffmpeg(), "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"])
    return parse_mean(r.stderr)


# ---------------------------------------------------------------- setup

def _long(cmd, label, env):
    """Run a long command, its output into the log, a heartbeat line every minute."""
    with open(LOG, "a", encoding="utf-8", errors="replace") as lf:
        lf.write("\n$ %s\n" % " ".join(str(c) for c in cmd))
        lf.flush()
        p = subprocess.Popen([str(c) for c in cmd], stdout=lf, stderr=subprocess.STDOUT, env=env)
        t0 = time.time()
        last = t0
        while p.poll() is None:
            time.sleep(2)
            if time.time() - last >= 60:
                last = time.time()
                say("WORKING %s, %d min so far" % (label, int((last - t0) // 60)))
        return p.returncode


def _tail_log(n=6):
    try:
        lines = LOG.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        return " | ".join(l.strip() for l in lines[-n:] if l.strip())[-900:]
    except Exception:
        return ""


def _do_setup():
    env = child_env()
    t0 = time.time()
    uv = vbin(BOOT) / ("uv.exe" if WIN else "uv")
    _step(1)
    # 1) uv, a small installer that also brings its own Python, so the Python on this computer does not matter.
    if uv.exists():
        say("STEP 1/4 OK installer already here")
    else:
        if not vpy(BOOT).exists():
            r = run([sys.executable, "-m", "venv", BOOT])
            if r.returncode != 0:
                say("SETUP_FAILED step 1 could not create a Python environment: %s" % (r.stderr.strip()[-400:]))
                return 1
        rc = _long([vpy(BOOT), "-m", "pip", "install", "--disable-pip-version-check", "-q", "uv"], "installer", env)
        if rc != 0 or not uv.exists():
            say("SETUP_FAILED step 1 installer: %s" % _tail_log())
            return 1
        say("STEP 1/4 OK installer")
    _step(2)
    # 2) Python 3.12 inside the tool folder, and an environment on it.
    if vpy(ENV).exists():
        say("STEP 2/4 OK Python already here")
    else:
        rc = _long([uv, "venv", "--python", PY_VERSION, "--python-preference", "only-managed", ENV], "Python", env)
        if rc != 0 or not vpy(ENV).exists():
            say("SETUP_FAILED step 2 Python: %s" % _tail_log())
            return 1
        say("STEP 2/4 OK Python %s" % PY_VERSION)
    _step(3)
    # 3) the packages: Demucs (with torch, the big one), yt-dlp, ffmpeg, and deno that YouTube downloads need.
    check = [vpy(ENV), "-c", "import demucs.api, yt_dlp, imageio_ffmpeg, torch; print(torch.__version__)"]
    if run(check, env=env).returncode == 0:
        say("STEP 3/4 OK packages already here")
    else:
        say("STEP 3/4 downloading the packages, this is the long part")
        rc = _long([uv, "pip", "install", "--python", vpy(ENV)] + PACKAGES, "packages", env)
        if rc != 0:
            # deno is only a helper for YouTube; never let it block the rest
            rc = _long([uv, "pip", "install", "--python", vpy(ENV)] + [p for p in PACKAGES if p != "deno"], "packages", env)
        if rc != 0 or run(check, env=env).returncode != 0:
            say("SETUP_FAILED step 3 packages: %s" % _tail_log())
            return 1
        say("STEP 3/4 OK packages")
    _step(4)
    # 4) the separation model itself (about 80 MB), so the first song does not wait for it.
    smoke = ("import numpy as np, torch; from demucs.api import Separator; "
             "w = torch.from_numpy(np.zeros((2, 88200), dtype=np.float32)); "
             "_, st = Separator(model='htdemucs', device='cpu', progress=False).separate_tensor(w, 44100); "
             "assert 'vocals' in st; print('model ok')")
    rc = _long([vpy(ENV), "-c", smoke], "model", env)
    if rc != 0:
        say("SETUP_FAILED step 4 model: %s" % _tail_log())
        return 1
    say("STEP 4/4 OK model")
    _long([uv, "cache", "clean"], "cleanup", env)
    info = run([vpy(ENV), "-c", "import torch, yt_dlp.version as v, imageio_ffmpeg as f; print(torch.__version__, v.__version__, f.get_ffmpeg_version())"], env=env).stdout.strip()
    READY_FILE.write_text(json.dumps({"version": VERSION, "when": time.strftime("%Y-%m-%d %H:%M"), "versions": info}), encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    SONGS.mkdir(parents=True, exist_ok=True)
    say("SETUP OK in %d min | %s | tools in %s | your files go to %s" % (int((time.time() - t0) // 60), info, TOOL, OUT))
    return 0



STATE = TOOL / "setup.state"
SETUP_WAIT = 500.0   # the front waits this long, then returns before the agent's ten minute limit
_CUR = {"step": 0}


def _write_state(step, note=""):
    try:
        tmp = STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"t": time.time(), "step": step, "note": note}), encoding="utf-8")
        os.replace(str(tmp), str(STATE))
    except OSError:
        pass


def _read_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _step(n):
    _CUR["step"] = n
    _write_state(n)


def _worker_alive():
    st = _read_state()
    return bool(st) and isinstance(st.get("step"), int) and time.time() - st.get("t", 0) < 90


def cmd_setup_worker(args):
    """Runs detached from the agent, so a tool time limit never kills a download halfway."""
    import threading

    def beat():
        while True:
            time.sleep(10)
            if isinstance(_CUR["step"], int):
                _write_state(_CUR["step"])
    threading.Thread(target=beat, daemon=True).start()
    try:
        rc = _do_setup()
    except Exception as e:
        say("SETUP_FAILED %s" % e)
        rc = 1
    _CUR["step"] = "done" if rc == 0 else "failed"
    _write_state(_CUR["step"], "" if rc == 0 else _tail_log(3))
    return rc


def _spawn_worker():
    _write_state(0, "starting")
    lf = open(LOG, "a", encoding="utf-8", errors="replace")
    cmd = [sys.executable, str(Path(__file__).resolve()), "_setup_worker"]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    kw = dict(stdin=subprocess.DEVNULL, stdout=lf, stderr=subprocess.STDOUT, close_fds=True, env=env, cwd=str(TOOL))
    if WIN:
        base = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        try:
            subprocess.Popen(cmd, creationflags=base | 0x01000000, **kw)  # and CREATE_BREAKAWAY_FROM_JOB when allowed
        except OSError:
            subprocess.Popen(cmd, creationflags=base, **kw)
    else:
        subprocess.Popen(cmd, start_new_session=True, **kw)


def cmd_setup(args):
    if ready():
        say("SETUP OK already installed | tools in %s | your files go to %s" % (TOOL, OUT))
        return 0
    TOOL.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(str(HOME)).free / 1e9
    if free < 2:
        say("LOW_DISK %.1f GB free, setup needs about 2 GB free (it takes about 1 GB). Free some space and run setup again." % free)
        return 4
    if _worker_alive():
        say("SETUP already running in the background, waiting for it")
    else:
        _spawn_worker()
        say("SETUP started in the background. First time only, 5 to 15 minutes on normal internet, longer on slow internet.")
    wait = float(os.environ.get("MUSIC_BED_SETUP_WAIT", SETUP_WAIT))
    t0 = time.time()
    last = t0
    while time.time() - t0 < wait:
        time.sleep(2)
        if ready():
            info = json.loads(READY_FILE.read_text(encoding="utf-8"))
            say("SETUP OK | %s | tools in %s | your files go to %s" % (info.get("versions", ""), TOOL, OUT))
            return 0
        st = _read_state() or {}
        if st.get("step") == "failed":
            say("SETUP_FAILED %s" % (st.get("note") or _tail_log(3)))
            return 1
        if not _worker_alive() and time.time() - t0 > 30:
            say("SETUP_FAILED the background install stopped. Run setup again, it continues from where it stopped. | %s" % _tail_log(3))
            return 1
        if time.time() - last >= 60:
            last = time.time()
            say("WORKING step %s of 4, %d min" % (st.get("step", "?"), int((last - t0) // 60)))
    st = _read_state() or {}
    say("SETUP_RUNNING step %s of 4, still installing in the background. Run setup again to keep waiting." % st.get("step", "?"))
    return 5


def cmd_status(args):
    if not ready():
        if _worker_alive():
            say("SETUP_RUNNING step %s of 4, installing in the background" % (_read_state() or {}).get("step", "?"))
        else:
            say("SETUP_NEEDED %s" % ("everything" if not TOOL.exists() else "setup did not finish"))
    else:
        info = json.loads(READY_FILE.read_text(encoding="utf-8"))
        say("READY since %s | output folder %s" % (info.get("when", "?"), OUT))
    if SONGS.exists():
        for d in sorted(p for p in SONGS.iterdir() if p.is_dir()):
            c = d / "check.json"
            v = json.loads(c.read_text(encoding="utf-8")).get("verdict", "?") if c.exists() else "not split yet"
            say("SONG %s | %s" % (d.name, v))
    return 0


# ---------------------------------------------------------------- the three actions (run inside the env)

def ytdlp(args):
    return [sys.executable, "-m", "yt_dlp", "--no-playlist", "--no-warnings"] + args


def find_original(d):
    for p in sorted(d.glob("original.*")):
        if p.suffix.lower() in AUDIO_EXT or p.suffix.lower() in VIDEO_EXT:
            return p
    return None


def cmd_get(args):
    if not args:
        say("USAGE get \"<artist and song>\" or get <link>")
        return 2
    q = " ".join(a for a in args if a not in ("--again", "--long")).strip()
    again = "--again" in args
    allow_long = "--long" in args
    target = q if re.match(r"https?://", q) else "ytsearch1:" + q
    r = run(ytdlp(["--skip-download", "--print", "%(id)s\t%(title)s\t%(channel)s\t%(duration)s\t%(webpage_url)s", target]), env=os.environ)
    line = next((l for l in r.stdout.splitlines() if "\t" in l), "")
    if r.returncode != 0 or not line:
        err = (r.stderr.strip().splitlines() or ["no result"])[-1][:400]
        say("DOWNLOAD_FAILED %s" % err)
        return 1
    vid, title, channel, dur, url = (line.split("\t") + [""] * 5)[:5]
    try:
        secs = int(float(dur))
    except ValueError:
        secs = 0
    slug = slugify(title)
    d = SONGS / slug
    say("FOUND %s | %s | %d:%02d | %s" % (title, channel, secs // 60, secs % 60, url))
    if secs > 15 * 60 and not allow_long:
        say("WARNING_LONG this result is %d minutes, probably a mix or a loop and not the song. Nothing was downloaded. Search again, or add --long if this is really it." % (secs // 60))
        return 1
    old = find_original(d) if d.exists() else None
    if old and not again:
        remember(d)
        say("ALREADY %s" % old)
        say("FOLDER %s" % d)
        return 0
    d.mkdir(parents=True, exist_ok=True)
    for p in d.glob("original.*"):
        p.unlink()
    r = run(ytdlp(["-f", "bestaudio[ext=m4a]/bestaudio/best", "-o", str(d / "original.%(ext)s"), url]), env=os.environ)
    got = find_original(d)
    if r.returncode != 0 or not got:
        err = (r.stderr.strip().splitlines() or ["unknown error"])[-1][:400]
        say("DOWNLOAD_FAILED %s" % err)
        return 1
    (d / "source.txt").write_text("%s | %s | %s | %s\n" % (title, channel, dur, url), encoding="utf-8")
    remember(d)
    say("SAVED %s" % got)
    say("FOLDER %s" % d)
    return 0


def remember(d):
    try:
        LAST_FILE.write_text(json.dumps({"folder": str(d)}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def resolve_song(arg):
    """last, a song folder, an audio file anywhere, or a name of a song already saved."""
    d = _resolve_song(arg)
    if d:
        remember(d)
    return d


def _resolve_song(arg):
    if arg.strip().lower() == "last":
        try:
            d = Path(json.loads(LAST_FILE.read_text(encoding="utf-8"))["folder"])
            if find_original(d):
                return d
        except Exception:
            pass
        say("NOT_FOUND last (no song was downloaded yet, run get first)")
        return None
    p = Path(arg).expanduser()
    if p.is_dir() and find_original(p):
        return p
    if p.is_file():
        try:
            p.resolve().relative_to(SONGS.resolve())
            return p.parent
        except ValueError:
            base = slugify(p.stem)
            d, n = SONGS / base, 2
            while find_original(d) and find_original(d).stat().st_size != p.stat().st_size:
                d, n = SONGS / ("%s-%d" % (base, n)), n + 1   # same name, different file: a new folder
            d.mkdir(parents=True, exist_ok=True)
            if not find_original(d):
                shutil.copy2(str(p), str(d / ("original" + p.suffix.lower())))
            return d
    if SONGS.exists():
        key = slugify(arg)
        dirs = [x for x in SONGS.iterdir() if x.is_dir() and find_original(x)]
        exact = [x for x in dirs if x.name == key]
        if exact:
            return exact[0]
        words = [w for w in key.split("-") if len(w) > 1]
        hits = [x for x in dirs if words and all(w in x.name for w in words)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            say("AMBIGUOUS %s" % " | ".join(h.name for h in hits))
            return None
    say("NOT_FOUND %s (run get first, or give the path of an audio file)" % arg)
    return None


def write_mp3(tensor, path):
    import numpy as np
    a = tensor.detach().cpu().numpy().astype(np.float32)
    peak = float(np.abs(a).max()) if a.size else 0.0
    if peak > 0.99:
        a = a * (0.99 / peak)
    raw = np.ascontiguousarray(a.T).tobytes()
    tmp = path.with_suffix(".part.mp3")
    p = subprocess.run([ffmpeg(), "-v", "error", "-y", "-f", "f32le", "-ar", "44100", "-ac", "2", "-i", "-",
                        "-c:a", "libmp3lame", "-b:a", "256k", str(tmp)], input=raw, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", "replace")[-300:])
    os.replace(str(tmp), str(path))


CHUNK = 60.0          # seconds of song per piece; each piece is saved, so a stopped split continues
CONTEXT = 2.0         # extra seconds on each side of a piece, so the joins are not heard
TIME_BUDGET = 480.0   # stop cleanly before the agent's ten minute limit, and say how to continue


def chunk_plan(n, sr=44100, chunk=CHUNK, ctx=CONTEXT):
    """[(keep_start, keep_end, read_start, read_end)] in samples."""
    step, c = int(chunk * sr), int(ctx * sr)
    out, a = [], 0
    while a < n:
        b = min(n, a + step)
        out.append((a, b, max(0, a - c), min(n, b + c)))
        a = b
    return out


def separate(d, budget=TIME_BUDGET):
    """Returns (done, total). Pieces land in <song>/.parts and survive a stop."""
    import numpy as np
    import torch
    from demucs.api import Separator
    t0 = time.time()
    src = find_original(d)
    p = subprocess.run([ffmpeg(), "-v", "error", "-i", str(src), "-map", "0:a:0", "-f", "f32le", "-ac", "2", "-ar", "44100", "-"],
                       capture_output=True)
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError("could not read the song: " + p.stderr.decode("utf-8", "replace")[-300:])
    wav = np.frombuffer(p.stdout, dtype=np.float32).reshape(-1, 2).T
    plan = chunk_plan(wav.shape[1])
    parts = d / ".parts"
    parts.mkdir(exist_ok=True)
    stamp = parts / "plan.json"
    sig = {"samples": int(wav.shape[1]), "chunk": CHUNK, "context": CONTEXT, "source": src.name}
    if not stamp.exists() or json.loads(stamp.read_text(encoding="utf-8")) != sig:
        for f in parts.glob("*.npy"):
            f.unlink()
        stamp.write_text(json.dumps(sig), encoding="utf-8")
    sep = None
    slowest = 0.0
    for i, (ka, kb, ra, rb) in enumerate(plan):
        out = parts / ("%03d.npy" % i)
        if out.exists():
            continue
        if time.time() - t0 + slowest * 1.3 > budget:
            done = len(list(parts.glob("[0-9]*.npy")))
            return done, len(plan)
        t1 = time.time()
        if sep is None:
            sep = Separator(model="htdemucs", device="cpu", progress=False)
        _, stems = sep.separate_tensor(torch.from_numpy(wav[:, ra:rb].copy()), 44100)
        voc = stems["vocals"].detach().cpu().numpy()
        rest = sum(v for k, v in stems.items() if k != "vocals").detach().cpu().numpy()
        piece = np.stack([rest, voc])[:, :, ka - ra:kb - ra].astype(np.float32)
        np.save(str(out.with_suffix(".tmp.npy")), piece)
        os.replace(str(out.with_suffix(".tmp.npy")), str(out))
        slowest = max(slowest, time.time() - t1)
        say("WORKING piece %d of %d done" % (i + 1, len(plan)))
    full = np.concatenate([np.load(str(parts / ("%03d.npy" % i))) for i in range(len(plan))], axis=2)
    write_mp3(torch.from_numpy(full[0]), d / "instrumental.mp3")
    write_mp3(torch.from_numpy(full[1]), d / "vocals.mp3")
    shutil.rmtree(str(parts), ignore_errors=True)
    return len(plan), len(plan)


def run_check(d):
    mix = mean_volume(find_original(d))
    voc = mean_volume(d / "vocals.mp3")
    code, gap = verdict(mix, voc)
    data = {"mix_mean_db": mix, "vocal_mean_db": voc, "gap_db": gap, "verdict": code, "use": auto_use(code)}
    (d / "check.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def report_check(c):
    say("VERDICT %s | mix %s dB, vocals %s dB, gap %s dB | auto uses %s" % (
        c["verdict"], c["mix_mean_db"], c["vocal_mean_db"], c["gap_db"], c["use"]))


def cmd_split(args):
    if not args:
        say("USAGE split \"<song>\"")
        return 2
    again = "--again" in args
    d = resolve_song(" ".join(a for a in args if a != "--again"))
    if not d:
        return 1
    if again and not (d / ".parts").exists():
        for f in ("instrumental.mp3", "vocals.mp3", "check.json"):
            if (d / f).exists():
                (d / f).unlink()
    if (d / "instrumental.mp3").exists() and (d / "check.json").exists() and not (d / ".parts").exists():
        say("ALREADY %s" % (d / "instrumental.mp3"))
        report_check(json.loads((d / "check.json").read_text(encoding="utf-8")))
        return 0
    src = find_original(d)
    info = probe(src)
    secs = parse_duration(info) or 0
    say("SPLITTING %s (%d:%02d), in pieces of a minute each" % (d.name, int(secs) // 60, int(secs) % 60))
    t0 = time.time()
    try:
        done, total = separate(d, float(os.environ.get("MUSIC_BED_BUDGET", TIME_BUDGET)))
    except Exception as e:  # report, never a traceback wall
        say("SPLIT_FAILED %s" % str(e)[-400:])
        return 1
    if done < total:
        say("SPLIT_PARTIAL %d of %d pieces done in %d s. Run split again, it continues from piece %d." % (done, total, int(time.time() - t0), done + 1))
        return 5
    say("SPLIT_OK in %d s | %s" % (int(time.time() - t0), d / "instrumental.mp3"))
    report_check(run_check(d))
    return 0


def parse_time(v):
    """Seconds from '75', '75.5', '1:15' or '0:01:15'. None when it is not a time."""
    try:
        parts = [float(x) for x in str(v).strip().split(":")]
    except ValueError:
        return None
    if not parts or len(parts) > 3 or any(x < 0 for x in parts):
        return None
    t = 0.0
    for x in parts:
        t = t * 60 + x
    return t


def _opt(args, name, default=None):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            v = args[i + 1]
            del args[i:i + 2]
            return v
    return default


def cmd_mix(args):
    args = list(args)
    start = parse_time(_opt(args, "--start", "0") or 0)
    use = _opt(args, "--use", "auto")
    try:
        level = float(_opt(args, "--level", "0") or 0)
    except ValueError:
        level = None
    if start is None or level is None:
        say("USAGE --start is seconds or m:ss (75 or 1:15), --level is a number of dB (-3 or 3)")
        return 2
    if len(args) < 2:
        say("USAGE mix \"<video>\" \"<song>\" [--start SEC] [--use auto|instrumental|original] [--level DB]")
        return 2
    video = Path(args[0]).expanduser()
    if not video.is_file():
        say("NOT_FOUND video %s" % video)
        return 1
    d = resolve_song(" ".join(args[1:]))
    if not d:
        return 1
    if use not in ("auto", "instrumental", "original"):
        say("USAGE --use is auto, instrumental or original")
        return 2
    if use in ("auto", "instrumental") and not (d / "check.json").exists():
        rc = cmd_split([str(d)])
        if rc != 0:
            return rc  # SPLIT_PARTIAL (5) means: run mix again, the split continues
    chk = json.loads((d / "check.json").read_text(encoding="utf-8")) if (d / "check.json").exists() else None
    chosen = chk["use"] if (use == "auto" and chk) else ("original" if use == "auto" else use)
    bed = d / "instrumental.mp3" if chosen == "instrumental" else find_original(d)
    vinfo = probe(video)
    dur = parse_duration(vinfo)
    has_audio, vcodec = parse_streams(vinfo)
    if not dur or not vcodec:
        say("MIX_FAILED could not read the video %s" % video)
        return 1
    dur = round(dur, 3)
    bed_dur = parse_duration(probe(bed)) or 0
    if bed_dur and start >= bed_dur:
        say("MIX_FAILED --start %.1f is after the end of the song (%.1f s)" % (start, bed_dur))
        return 1
    if bed_dur and bed_dur - start < dur:
        say("WARNING_SHORT_SONG the music ends at %.1f s and the video is %.1f s. An earlier --start fixes it." % (bed_dur - start, dur))
    voice = lufs(video) if has_audio else None
    has_voice = voice is not None and voice > -60
    keep_audio = has_audio   # never drop the video's own sound, even when it measures silent
    bed_i = lufs(bed, start, dur)
    gain, key, target = plan_levels(bed_i, voice, level)
    OUT.mkdir(parents=True, exist_ok=True)
    out = out_name(video, d.name)
    tmp = out.with_name(out.stem + ".part.mp4")
    fc = build_filter(dur, gain, key, keep_audio)
    base = [ffmpeg(), "-v", "error", "-y", "-i", str(video), "-ss", "%.3f" % start, "-i", str(bed),
            "-filter_complex", fc, "-map", "0:v:0", "-map", "[a]", "-t", "%.3f" % dur]
    tail = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(tmp)]
    if vcodec in ("h264", "hevc"):
        vargs = ["-c:v", "copy"] + (["-tag:v", "hvc1"] if vcodec == "hevc" else [])
    else:
        vargs = ["-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p"]
    say("MIXING %s + %s (%s, from %.1f s) | video %.1f s | voice %s | bed %s LUFS, gain %s dB" % (
        video.name, d.name, chosen, start, dur, ("%s LUFS" % voice) if has_voice else "none, music only", bed_i, gain))
    r = run(base + vargs + tail)
    if r.returncode != 0 and vargs[1] == "copy":
        r = run(base + ["-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p"] + tail)
    if r.returncode != 0 or not tmp.exists():
        if tmp.exists():
            tmp.unlink()
        say("MIX_FAILED %s" % r.stderr.strip()[-400:])
        return 1
    os.replace(str(tmp), str(out))
    final = lufs(out)
    say("MIXED %s" % out)
    say("LOUDNESS %s LUFS integrated | music %s from %.1f s, target %s LUFS, level %+.1f dB" % (final, chosen, start, target, level))
    if chk:
        report_check(chk)
    return 0


def cmd_open(args):
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        if WIN:
            os.startfile(str(OUT))  # noqa
        elif sys.platform == "darwin":
            subprocess.run(["open", str(OUT)])
        else:
            subprocess.run(["xdg-open", str(OUT)])
    except Exception as e:
        say("OPEN_FAILED %s | the folder is %s" % (e, OUT))
        return 1
    say("OPENED %s" % OUT)
    return 0


def cmd_update(args):
    uv = vbin(BOOT) / ("uv.exe" if WIN else "uv")
    rc = _long([uv, "pip", "install", "--python", vpy(ENV), "-U", "yt-dlp[default]", "deno"], "update", child_env())
    say("UPDATE_OK" if rc == 0 else "UPDATE_FAILED %s" % _tail_log())
    return rc


# ---------------------------------------------------------------- selftest

def cmd_selftest(args):
    fails = []

    def t(cond, what):
        if not cond:
            fails.append(what)

    t(sys.version_info >= (3, 8), "python 3.8 or newer")
    t(slugify("Booker T. & The MG's - Green Onions (Official Audio)") == "booker-t-the-mgs-green-onions", "slug english")
    t(slugify("Pink Floyd - Money (2023 Remaster)") == "pink-floyd-money", "slug remaster")
    t(slugify("עומר אדם - תגידו לה [Official Video]") == "עומר-אדם-תגידו-לה", "slug hebrew")
    t(slugify('a<b>c:"d"/e\\f|g?h*') == "a-b-c-d-e-f-g-h", "slug windows chars")
    t(slugify("((()))") == "song", "slug empty")
    # the nine songs of 29.10.2026, mix mean vs vocal stem mean
    table = [("let-it-happen", -10.7, -20.9, "OK"), ("every-living-breathing-moment", -13.3, -34.6, "ALMOST_INSTRUMENTAL"),
             ("veridis-quo", -15.4, -34.0, "ALMOST_INSTRUMENTAL"), ("beanie-slowed", -13.5, -21.2, "OK"),
             ("soulful-strut", -16.2, -75.8, "NO_VOCALS"), ("green-onions", -16.6, -60.3, "NO_VOCALS"),
             ("touch-the-sky", -9.9, -16.9, "HEAVY_VOCALS"), ("money", -17.0, -26.9, "OK"),
             ("false-prophets", -10.7, -15.6, "HEAVY_VOCALS")]
    for name, mix, voc, want in table:
        t(verdict(mix, voc)[0] == want, "verdict " + name)
    t(auto_use("ALMOST_INSTRUMENTAL") == "original" and auto_use("OK") == "instrumental", "auto use")
    info = ("Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'a.mp4':\n  Duration: 00:01:02.50, start: 0.000000, bitrate: 1 kb/s\n"
            "  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p, 1080x1920\n"
            "  Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), 48000 Hz, stereo\n")
    t(parse_duration(info) == 62.5, "duration")
    t(parse_streams(info) == (True, "h264"), "streams")
    t(parse_streams(info.replace("Audio: aac", "Data: none")) == (False, "h264"), "streams no audio")
    t(parse_lufs("  Integrated loudness:\n    I:         -14.4 LUFS\n    Threshold: -24.6 LUFS\n") == -14.4, "lufs")
    t(parse_lufs("    I:         -inf LUFS\n") == -70.0, "lufs silent")
    t(parse_mean("[Parsed_volumedetect_0 @ 0x1] mean_volume: -34.0 dB\n") == -34.0, "mean")
    # with a voice at the reference level this is exactly bed-mix.sh: gain = -22.4 - bed, no key change
    t(plan_levels(-8.4, -15.0) == (-14.0, 0.0, -22.4), "levels proven recipe")
    g, k, tg = plan_levels(-8.4, -25.0)
    t(tg == -32.4 and k == 10.0, "levels quiet voice")
    t(plan_levels(-8.4, None) == (-7.6, 0.0, -16.0), "levels no voice, music alone")
    t(plan_levels(-80, -15.0)[0] == 0.0, "levels silent bed")
    fc = build_filter(12.0, -14.0, 0.0, True)
    for part in ("threshold=0.03:ratio=5:attack=15:release=350", "afade=t=in:d=0.15", "afade=t=out:st=11.0:d=1.0",
                 "normalize=0", "alimiter=limit=0.89"):
        t(part in fc, "filter " + part)
    t("[0:a]" not in build_filter(12.0, -14.0, 0.0, False), "filter no voice")
    t(str(OUT).endswith("מוזיקה לריל") and "Desktop" not in str(OUT), "output folder in home, not on the Desktop")
    t(out_name(Path("clip.mov"), "money").name.startswith("clip עם money"), "output name")
    plan = chunk_plan(44100 * 150)
    t(len(plan) == 3 and plan[0][:2] == (0, 44100 * 60) and plan[-1][1] == 44100 * 150, "pieces cover the song")
    t(all(p[1] == q[0] for p, q in zip(plan, plan[1:])), "pieces touch, no gap and no overlap kept")
    t(plan[1][2] == 44100 * 58 and plan[0][2] == 0, "pieces read context")
    t(parse_time("75") == 75 and parse_time("1:15") == 75 and parse_time("0:01:15") == 75 and parse_time("1:3x") is None, "start times")
    if fails:
        say("SELFTEST FAILED %s" % ", ".join(fails))
        return 1
    say("SELFTEST OK python %d.%d.%d | %s | tools go to %s | files go to %s" % (
        sys.version_info[0], sys.version_info[1], sys.version_info[2], "Windows" if WIN else sys.platform, TOOL, OUT))
    return 0


# ---------------------------------------------------------------- main

COMMANDS = {"selftest": cmd_selftest, "setup": cmd_setup, "_setup_worker": cmd_setup_worker, "status": cmd_status, "get": cmd_get, "split": cmd_split,
            "mix": cmd_mix, "open": cmd_open, "update": cmd_update}
NEEDS_ENV = {"get", "split", "mix", "update"}


def main(argv):
    _utf8_console()
    if not argv or argv[0] not in COMMANDS:
        say("USAGE %s" % " | ".join(COMMANDS))
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd in NEEDS_ENV and cmd != "update" and not in_env():
        if not ready():
            say("SETUP_NEEDED run setup first")
            return 3
        return subprocess.call([str(vpy(ENV)), str(Path(__file__).resolve()), cmd] + rest, env=child_env())
    if cmd == "update" and not ready():
        say("SETUP_NEEDED run setup first")
        return 3
    return COMMANDS[cmd](rest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
