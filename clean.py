
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cross-platform Python project cleaner
------------------------------------
Usage:
  python clean.py                # interactive confirm (safe defaults)
  python clean.py --yes          # no prompt
  python clean.py --dry-run      # show what would be deleted
  python clean.py --add-glob "pic*" --add-glob "*.tmp"
  python clean.py --write-gitignore   # create a .gitignore from template
  python clean.py --path /my/project  # clean a different folder

Safe defaults:
- Removes common Python/Jupyter/test caches and OS junk.
- Skips version-control folders (.git, .hg), virtual envs (.venv, venv), and node_modules.
- You can add/remove patterns via CLI flags.
"""
import argparse
import fnmatch
import os
import shutil
from pathlib import Path

DEFAULT_DIRS = {
    "__pycache__", ".ipynb_checkpoints", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".hypothesis", ".tox", ".nox",
    "htmlcov", "dist", "build", "*.egg-info"
}
DEFAULT_FILE_EXTS = {".pyc", ".pyo", ".pyd", ".pydist", ".so", ".DS_Store"}
DEFAULT_FILE_GLOBS = {".coverage", "coverage.xml", "*.log", "*.tmp", "*.temp"}

# Directories we never descend into (safety)
SKIP_DIRS = {".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", ".idea", ".vscode"}

GITIGNORE_TEMPLATE = """# --- Python ---
__pycache__/
*.py[cod]
*.pyd
*.pyo
*.pyc

# --- Environments ---
.venv/
venv/
env/
.env
.env.*

# --- Jupyter / Tests / Linters ---
.ipynb_checkpoints/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.hypothesis/
.tox/
.nox/
.coverage
coverage.xml
htmlcov/

# --- Build / Dist ---
dist/
build/
*.egg-info/

# --- OS junk ---
.DS_Store
Thumbs.db

# --- Logs ---
logs/
*.log

# --- Data & Models (keep samples) ---
data/*
!data/sample*
!data/README.md
models/*
!models/README.md
"""

def match_any(name: str, patterns):
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)

def should_skip_dir(dirname: str):
    return dirname in SKIP_DIRS or match_any(dirname, SKIP_DIRS)

def collect_targets(root: Path, add_dirs, add_exts, add_globs, exclude_dirs, exclude_globs):
    dirs_to_remove = set(DEFAULT_DIRS) | set(add_dirs or [])
    file_exts = set(DEFAULT_FILE_EXTS) | set(add_exts or [])
    file_globs = set(DEFAULT_FILE_GLOBS) | set(add_globs or [])

    targets = {"files": [], "dirs": []}
    for cur, dirnames, filenames in os.walk(root, topdown=True):
        # prune directories we never want to enter
        pruned = []
        for d in list(dirnames):
            if should_skip_dir(d) or match_any(d, exclude_dirs or []) or match_any(d, exclude_globs or []):
                pruned.append(d)
        for d in pruned:
            dirnames.remove(d)

        # consider directories for deletion
        for d in list(dirnames):
            if d in dirs_to_remove or match_any(d, dirs_to_remove):
                # Also respect excludes
                if (exclude_dirs and d in exclude_dirs) or (exclude_globs and match_any(d, exclude_globs)):
                    continue
                targets["dirs"].append(Path(cur) / d)

        # consider files for deletion
        for f in filenames:
            p = Path(cur) / f
            ext = p.suffix.lower()
            if ext in file_exts or match_any(f, file_globs):
                if exclude_globs and match_any(f, exclude_globs):
                    continue
                targets["files"].append(p)

    return targets

def human_preview(targets):
    files = sorted(map(str, targets["files"]))
    dirs = sorted(map(str, targets["dirs"]))
    return f"Files: {len(files)}\nDirs: {len(dirs)}"

def delete_targets(targets, dry_run=False):
    deleted_files = 0
    deleted_dirs = 0
    for d in sorted(set(targets["dirs"]), key=lambda p: -len(str(p))):
        if dry_run: 
            print(f"[DRY] rm -rf {d}")
        else:
            shutil.rmtree(d, ignore_errors=True)
            print(f"Deleted dir: {d}")
            deleted_dirs += 1
    for f in targets["files"]:
        if dry_run:
            print(f"[DRY] rm {f}")
        else:
            try:
                os.remove(f)
                print(f"Deleted file: {f}")
                deleted_files += 1
            except FileNotFoundError:
                pass
    return deleted_files, deleted_dirs

def write_gitignore(dest: Path):
    gi = dest / ".gitignore"
    if gi.exists():
        print(f".gitignore already exists at {gi}. Showing template below:\n")
        print(GITIGNORE_TEMPLATE)
        return gi, False
    gi.write_text(GITIGNORE_TEMPLATE, encoding="utf-8")
    print(f"Wrote .gitignore template to {gi}")
    return gi, True

def main():
    ap = argparse.ArgumentParser(description="Cross-platform Python project cleanup tool")
    ap.add_argument("--path", default=".", help="Target project path (default: .)")
    ap.add_argument("--add-dir", action="append", help="Extra directory name/glob to remove (repeatable)")
    ap.add_argument("--add-ext", action="append", help="Extra file extension to remove (e.g., .png) (repeatable)")
    ap.add_argument("--add-glob", action="append", help="Extra file glob to remove (e.g., 'pic*') (repeatable)")
    ap.add_argument("--exclude-dir", action="append", help="Directory names to exclude (repeatable)")
    ap.add_argument("--exclude-glob", action="append", help="Glob patterns to exclude (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="Preview deletions without removing")
    ap.add_argument("--yes", "-y", action="store_true", help="Do not prompt for confirmation")
    ap.add_argument("--write-gitignore", action="store_true", help="Create a .gitignore template if missing")
    args = ap.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        raise SystemExit(f"Path not found: {root}")

    if args.write_gitignore:
        write_gitignore(root)

    targets = collect_targets(
        root=root,
        add_dirs=args.add_dir,
        add_exts=args.add_ext,
        add_globs=args.add_glob,
        exclude_dirs=args.exclude_dir,
        exclude_globs=args.exclude_glob,
    )
    print("=== Cleanup Plan ===")
    print(human_preview(targets))

    if not args.yes and not args.dry_run:
        try:
            resp = input("Proceed with deletion? [y/N] ").strip().lower()
        except EOFError:
            resp = "n"
        if resp not in {"y", "yes"}:
            print("Aborted.")
            return

    deleted_files, deleted_dirs = delete_targets(targets, dry_run=args.dry_run)
    if args.dry_run:
        print("Dry run complete ✅")
    else:
        print(f"Cleanup complete ✅  (files: {deleted_files}, dirs: {deleted_dirs})")

if __name__ == "__main__":
    main()
