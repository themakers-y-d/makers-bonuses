#!/usr/bin/env python3
"""Turns the sound of a video or recording into text with times, on the owner's own computer.

Usage:  bash run.sh transcribe.py FILE [--lang he|en|auto] [--model ivrit|medium|small] [--out FILE]
        bash run.sh transcribe.py --check          (says what is already installed)

Nothing leaves the computer and nothing is paid for. The models are the MAKERS video editor's, at the same pinned
commits, in ~/reel-studio/models, so a model another MAKERS gift downloaded is reused: ivrit (Hebrew, about
1.6 GB, the default for Hebrew), medium (about 1.5 GB) or small (about 0.5 GB, the default for English when
ivrit is the only one around is fine too). A missing model downloads the first time and continues where it
stopped if the connection drops. While it downloads it prints the size so far every 15 seconds; while it
transcribes, a line every 30 seconds. Any problem prints a line starting "PROBLEM".

Get the words of a link or a file with get_source.py, which calls this file when there are no captions.
"""
import os, sys, threading, time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # the faster transfer stalled on home connections in the editor's tests
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # Hebrew names on a Windows code page would crash print
    except Exception:
        pass

STUDIO = Path(os.environ.get("REEL_STUDIO") or (Path.home() / "reel-studio"))
MODELS = {"ivrit": "ivrit-ai/whisper-large-v3-turbo-ct2",
          "medium": "Systran/faster-whisper-medium",
          "small": "Systran/faster-whisper-small"}
REVISIONS = {"ivrit-ai/whisper-large-v3-turbo-ct2": "72ad623a37947395efcc3933132353790e5a12f5",
             "Systran/faster-whisper-medium": "08e178d48790749d25932bbc082711ddcfdfbc4f",
             "Systran/faster-whisper-small": "536b0662742c02347bc0e980a01041f333bce120"}


def say(msg):
    print(msg, flush=True)


def die(msg):
    say("PROBLEM " + msg)
    sys.exit(1)


def installed_models():
    # a model counts only when its pinned snapshot has the weights: an interrupted download leaves the folder behind
    mdir = STUDIO / "models"
    return [k for k, repo in MODELS.items()
            if (mdir / ("models--" + repo.replace("/", "--")) / "snapshots" / REVISIONS[repo] / "model.bin").is_file()]


def libs_ok():
    try:
        import faster_whisper, av  # noqa: F401
        return True
    except ImportError:
        return False


def check():
    have = installed_models()
    say("LIBS OK" if libs_ok() else "LIBS MISSING")
    say("MODELS " + (" ".join(have) if have else "none"))
    say("READY" if libs_ok() and have else "NOT READY")


def folder_gb(d):
    total = 0
    for root, _dirs, files in os.walk(d, onerror=lambda e: None):
        for f in files:
            fp = os.path.join(root, f)
            try:
                if not os.path.islink(fp):
                    total += os.stat(fp, follow_symlinks=False).st_size
            except OSError:
                continue
    return total / 1e9


def model_path(name):
    from faster_whisper.utils import download_model
    repo, mdir = MODELS[name], STUDIO / "models"
    mdir.mkdir(parents=True, exist_ok=True)
    try:
        return download_model(repo, cache_dir=str(mdir), revision=REVISIONS[repo], local_files_only=True)
    except Exception:
        pass
    say(f"downloading the {name} transcription model, once (it continues where it stopped if the connection drops)")
    stop = []

    def watch():
        while not stop:
            say(f"downloaded so far {folder_gb(mdir):.2f} GB")
            time.sleep(15)

    threading.Thread(target=watch, daemon=True).start()
    try:
        path = download_model(repo, cache_dir=str(mdir), revision=REVISIONS[repo])
        stop.append(1)
        for f in mdir.rglob("*.incomplete"):
            f.unlink(missing_ok=True)
        return path
    except Exception as e:
        stop.append(1)
        die(f"the {name} model did not download ({type(e).__name__}: {str(e)[:150]}). Check the internet "
            "connection and run the same command again; it continues where it stopped.")


def load(name):
    from faster_whisper import WhisperModel
    path = model_path(name)
    kw = {"device": "cpu", "compute_type": "int8"}
    try:
        return WhisperModel(path, **kw)
    except Exception as e:
        first = e
    if not str(path).isascii():
        # the model reader opens files with the old Windows code page, so a user folder with Hebrew letters
        # in its name defeats it: hand it the files from memory instead (as the video editor does)
        try:
            files = {f.name: f.read_bytes() for f in Path(path).iterdir() if f.is_file()}
            return WhisperModel(MODELS[name], files=files, **kw)
        except Exception as e:
            first = e
    die(f"the {name} model did not load ({type(first).__name__}: {str(first)[:150]}). Close other programs "
        "to free memory and run again, or use --model small.")


def pieces(audio, sr, shortest=12, longest=26):
    """Sample ranges of at most `longest` seconds, each cut at the quietest 50 ms between `shortest` and
    `longest` seconds into the piece. A sentence that crossed the model's 30-second window lost words in the
    carousel skill's tests, so no piece is ever that long."""
    import numpy as np
    hop = sr // 20
    n = len(audio) // hop
    if n == 0:
        return [(0, len(audio))]
    energy = np.sqrt(np.mean(audio[: n * hop].reshape(n, hop) ** 2, axis=1))
    out, start = [], 0
    while (len(audio) - start) / sr > longest:
        lo, hi = start // hop + shortest * 20, min(start // hop + longest * 20, n)
        cut = (lo + int(np.argmin(energy[lo:hi]))) * hop
        out.append((start, cut))
        start = cut
    out.append((start, len(audio)))
    return out


def pick_model(lang, asked=None):
    if asked:
        if asked not in MODELS:
            die(f"unknown model {asked}. Use one of {', '.join(MODELS)}")
        return asked
    have = installed_models()
    if lang == "he":
        return "ivrit"
    # English or unknown: the general models are better than the Hebrew-tuned one; reuse what is there
    for m in ("medium", "small"):
        if m in have:
            return m
    return "small"


def transcribe(path, lang="he", model=None, start=0.0, end=None):
    """Returns a list of (seconds, text). lang None means detect."""
    import av  # noqa: F401
    from faster_whisper.audio import decode_audio
    name = pick_model(lang, model)
    m = load(name)
    done = []

    def beat():
        t0 = time.time()
        while not done:
            time.sleep(30)
            if not done:
                say(f"still transcribing, {int(time.time() - t0)} seconds so far")

    threading.Thread(target=beat, daemon=True).start()
    try:
        audio = decode_audio(str(path), sampling_rate=16000)
    except Exception as e:
        done.append(1)
        die(f"cannot read the sound of {Path(path).name} ({type(e).__name__}). Is it a video or audio file?")
    sr = 16000
    a0 = int(max(0.0, start) * sr)
    a1 = len(audio) if end is None else min(len(audio), int(end * sr))
    audio = audio[a0:a1]
    if len(audio) < sr // 2:
        done.append(1)
        die("there is no sound in this part of the file.")
    say(f"transcribing {Path(path).name}, {len(audio) // sr} seconds, with the {name} model")
    # the video editor's settings: no silence filter (it dropped speech under a music bed) and no text carried
    # from piece to piece (long recordings drift)
    kw = {"language": lang, "vad_filter": False, "beam_size": 5, "condition_on_previous_text": False}
    lines = []
    try:
        for a, b in pieces(audio, sr):
            segments, _info = m.transcribe(audio[a:b], **kw)
            for s in segments:
                t = s.text.strip()
                if t:
                    lines.append((start + a / sr + s.start, t))
    except Exception as e:
        done.append(1)
        die(f"transcription failed ({type(e).__name__}: {str(e)[:150]}). Run the same command once more.")
    done.append(1)
    if not lines:
        die("no speech was found. Ask the owner for the script, or for a few lines of what was said.")
    return lines


def stamp(sec):
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--check":
        check()
        return
    if not libs_ok():
        die("the transcription libraries are not installed. Run install-tools.sh base and then libs.")

    def opt(name, default):
        if name in args:
            i = args.index(name)
            if i + 1 >= len(args):
                die(f"{name} needs a value")
            return args[i + 1]
        return default

    src = Path(args[0]).expanduser()
    if not src.is_file():
        die(f"no file at {src}. Write the full path in double quotes.")
    lang = opt("--lang", "he")
    lines = transcribe(src, None if lang == "auto" else lang, opt("--model", None))
    out = Path(opt("--out", str(src.with_suffix(".transcript.txt"))))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(f"[{stamp(t)}] {x}\n" for t, x in lines), encoding="utf-8")
    say(f"TRANSCRIBED {len(lines)} lines, saved to {out}")


if __name__ == "__main__":
    main()
