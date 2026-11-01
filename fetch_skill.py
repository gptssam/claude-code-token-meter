#!/usr/bin/env python3
"""Download a third-party skill file from its pinned commit and check its sha256.

    python3 fetch_skill.py caveman ultracave        # -> .skills_cache/<name>/SKILL.md
    python3 fetch_skill.py --check                  # only verify files already in .skills_cache/

Nothing is installed globally. run_trials.py copies the cached file into a fresh temp folder
as a *project* skill (.claude/skills/<name>/SKILL.md) for each trial and deletes nothing else.
Standard library only.
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCK = HERE / "skills.lock.json"
CACHE = HERE / ".skills_cache"


def load_lock(path=LOCK):
    return {k: v for k, v in json.loads(Path(path).read_text(encoding="utf-8")).items() if not k.startswith("_")}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def cached_path(name, cache=CACHE):
    return Path(cache) / name / "SKILL.md"


def verify(name, lock=None, cache=CACHE):
    """True if the cached file exists and matches the pinned sha256."""
    lock = lock or load_lock()
    p = cached_path(name, cache)
    return p.exists() and sha256(p.read_bytes()) == lock[name]["sha256"]


def fetch(name, lock=None, cache=CACHE, opener=urllib.request.urlopen):
    lock = lock or load_lock()
    if name not in lock:
        raise SystemExit(f"unknown skill {name!r} — add it to skills.lock.json first")
    e = lock[name]
    url = f"https://raw.githubusercontent.com/{e['repo']}/{e['ref']}/{e['path']}"
    with opener(url) as r:
        data = r.read()
    got = sha256(data)
    if got != e["sha256"]:
        raise SystemExit(f"sha256 mismatch for {name}: got {got}, pinned {e['sha256']} — not saved")
    p = cached_path(name, cache)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p, url


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    lock = load_lock()
    names = a.names or list(lock)
    if a.check:
        bad = [n for n in names if not verify(n, lock)]
        for n in names:
            print(f"{'OK ' if n not in bad else 'BAD'} {n} {cached_path(n)}")
        return 1 if bad else 0
    for n in names:
        p, url = fetch(n, lock)
        print(f"OK  {n} <- {url}\n    sha256 {lock[n]['sha256']} -> {p.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
