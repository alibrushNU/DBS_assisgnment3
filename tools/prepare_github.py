"""Create a small, checked source ZIP for manual GitHub upload; never publish it."""
import hashlib
import json
import os
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    ".dockerignore", ".gitignore", ".env.example", "Dockerfile", "render.yaml",
    "compose.yaml", "requirements.txt", "requirements-web.txt", "pytest.ini", "README.md",
)
SQL_FILES = ("schema.sql", "seed.sql", "accepted_paper_schedule.sql")


def source_files(root=ROOT):
    files = [root / name for name in ROOT_FILES]
    files += [root / "sql" / name for name in SQL_FILES]
    for directory in ("part1", "part2", "part3", "tests", "tools"):
        files += sorted((root / directory).glob("*.py"))
    files += sorted((root / "docs").glob("*.md"))
    return sorted(files)


def verify_sources(files, root=ROOT):
    local = dotenv_values(root / ".env")
    secrets = set()
    for key in ("PART1_DB_PASSWORD", "PART1_DATABASE_URL", "DATABASE_URL"):
        for value in (local.get(key), os.environ.get(key)):
            if value and len(value) >= 8 and value != "CHANGE_ME" and "USERNAME:PASSWORD" not in value:
                secrets.add(value.encode())
    token = re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("A source path escapes the project directory.")
        data = path.read_bytes()
        if any(secret in data for secret in secrets) or token.search(data):
            raise ValueError(f"Credential check failed for {path.relative_to(root)}; no archive written.")


def prepare(root=ROOT):
    files = source_files(root)
    verify_sources(files, root)
    output = root / "build"
    output.mkdir(exist_ok=True)
    archive = output / "github-ready.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as zipped:
        for path in files:
            zipped.write(path, path.relative_to(root).as_posix())
    manifest = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    (output / "github-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return archive, len(files)


if __name__ == "__main__":
    archive, count = prepare()
    print(f"Prepared {archive.name}: {count} source files; local credentials, caches, environments, and generated exports excluded.")
