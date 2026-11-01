#!/usr/bin/env python3
"""Turns the sound of a video into text, on the owner's own computer, for Claude Code or Codex.

Usage:  <studio python> transcribe.py VIDEO [--model ivrit|medium|small] [--lang he|auto] [--out FILE]
        <studio python> transcribe.py --check            (says what is already installed)

Runs with the Python in ~/reel-studio/.venv, the folder the MAKERS video editor also uses, so a model either
gift downloaded serves both. The models are the editor's, at the same pinned commits, in ~/reel-studio/models:
ivrit (Hebrew, about 1.6 GB, the default), medium (about 1.5 GB) or small (about 0.5 GB, less accurate in
Hebrew). A missing model downloads the first time and continues where it stopped if the connection drops.

While the model downloads it prints the size so far every 15 seconds; while it transcribes, a line every 30
seconds. Then "TRANSCRIPT <file>" and, last, "TRANSCRIBED <n> lines, saved to <file>". The text file has one
line per piece of speech the model heard, with no times. Any problem prints a line starting "PROBLEM".
A file with the same name from an earlier video is never overwritten: the new one gets -2, -3 and so on.
"""
import os, sys, threading, time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # the faster transfer stalled on home connections in the editor's tests
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # Hebrew names on a Windows code page would crash print
    except Exception:
        pass

STUDIO = Path.home() / "reel-studio"
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


def opt(args, name, default):
    if name in args:
        i = args.index(name)
        if i + 1 >= len(args):
            die(f"{name} needs a value")
        return args[i + 1]
    return default


def installed_models():
    # a model counts only when its pinned snapshot has the weights: an interrupted download leaves the folder behind
    mdir = STUDIO / "models"
    return [k for k, repo in MODELS.items()
            if (mdir / ("models--" + repo.replace("/", "--")) / "snapshots" / REVISIONS[repo] / "model.bin").is_file()]


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


def check():
    try:
        import faster_whisper, av  # noqa: F401
        libs = "LIBS OK"
    except ImportError as e:
        libs = "LIBS MISSING " + str(e.name)
    have = installed_models()
    say(libs)
    say("MODELS " + (" ".join(have) if have else "none"))
    say("READY" if libs == "LIBS OK" and have else "NOT READY")


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


def duration(video):
    import av
    try:
        with av.open(str(video)) as c:
            if not c.streams.audio:
                die("this video has no sound track, so there is nothing to transcribe. Ask for the script or "
                    "a few lines of what was said instead.")
            return (c.duration or 0) / 1e6
    except SystemExit:
        raise
    except Exception as e:
        die(f"cannot open {video.name} ({type(e).__name__}). Is it a video or audio file?")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--check":
        check()
        return
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        die("the transcription libraries are not installed. Run install-transcriber.sh base and then libs.")
    video = Path(args[0]).expanduser()
    if not video.is_file():
        die(f"no file at {video}. Write the full path in double quotes.")
    name = opt(args, "--model", None) or ("ivrit" if "ivrit" in installed_models() or not installed_models()
                                         else installed_models()[0])
    if name not in MODELS:
        die(f"unknown model {name}. Use one of {', '.join(MODELS)}")
    lang = opt(args, "--lang", "he")
    lang = None if lang == "auto" else lang
    out = Path(opt(args, "--out", str(Path.home() / "carousels" / "transcripts" / (video.stem + ".txt"))))
    if "--out" not in args:
        n = 2
        while out.exists():
            out = out.with_name(f"{video.stem}-{n}.txt")
            n += 1
    dur = duration(video)

    done = []

    def beat():
        start = time.time()
        while not done:
            time.sleep(30)
            if not done:
                say(f"still working, {int(time.time() - start)} seconds so far")

    model = load(name)
    threading.Thread(target=beat, daemon=True).start()
    say(f"transcribing {video.name}, {int(dur)} seconds of video, with the {name} model")
    kw = {"language": lang, "vad_filter": True, "beam_size": 5}
    if dur > 720:
        # a long recording drifts and invents text when each piece is fed the text before it, so it is not
        # (clip_timestamps would turn VAD off in faster-whisper 1.2.1, Romi 01.11)
        kw["condition_on_previous_text"] = False
    try:
        segments, _info = model.transcribe(str(video), **kw)
        lines = [s.text.strip() for s in segments if s.text.strip()]
    except Exception as e:
        done.append(1)
        die(f"transcription failed ({type(e).__name__}: {str(e)[:150]}). Run the same command once more.")
    done.append(1)
    if not lines:
        die("no speech was found in the video. Ask for the script or a few lines of what was said instead.")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    say(f"TRANSCRIPT {out}")
    say(f"TRANSCRIBED {len(lines)} lines, saved to {out}")


if __name__ == "__main__":
    main()
