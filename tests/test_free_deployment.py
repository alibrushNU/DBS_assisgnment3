"""Free-plan startup and public-source packaging regression checks."""
from pathlib import Path
import re
from zipfile import ZipFile

import pytest

from part1.db import make_engine
from part3 import serve
from tools.prepare_github import ROOT, prepare, source_files, verify_sources


def test_render_selects_only_free_resources_and_no_paid_hooks_or_disks():
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert re.findall(r"^\s+plan:\s*(\S+)", blueprint, flags=re.MULTILINE) == ["free", "free"]
    assert "preDeployCommand:" not in blueprint
    assert "diskSizeGB:" not in blueprint and "disk:" not in blueprint
    assert "property: connectionString" in blueprint
    assert 'autoDeployTrigger: "off"' in blueprint


def test_production_initializes_before_listening(monkeypatch):
    events = []
    monkeypatch.setattr(serve, "initialize", lambda: events.append("initialized"))
    monkeypatch.setattr(serve.uvicorn, "run", lambda app, **kwargs: events.append((app, kwargs)))
    monkeypatch.setenv("PORT", "10001")
    serve.main()
    assert events == ["initialized", ("part3.app:app", {"host": "0.0.0.0", "port": 10001})]


def test_failed_initialization_never_starts_the_web_server(monkeypatch):
    def fail():
        raise RuntimeError("Initialization failed")

    started = []
    monkeypatch.setattr(serve, "initialize", fail)
    monkeypatch.setattr(serve.uvicorn, "run", lambda *args, **kwargs: started.append(True))
    with pytest.raises(RuntimeError, match="Initialization failed"):
        serve.main()
    assert not started


def test_no_embedded_local_password_fallback():
    with pytest.raises(ValueError, match="PART1_DB_PASSWORD"):
        make_engine("postgresql+psycopg://csci341_part1@127.0.0.1:55431/csci341_a3_part1")


def test_github_package_contains_sources_and_excludes_local_artifacts():
    verify_sources(source_files())
    archive, count = prepare()
    with ZipFile(archive) as zipped:
        names = set(zipped.namelist())
        assert len(names) == count
        assert {"Dockerfile", "render.yaml", "part1/db.py", "part2/demo.py", "part3/serve.py", "sql/schema.sql", ".env.example"} <= names
        assert ".env" not in names
        assert not any(name.startswith(("build/", ".venv/", ".git/", ".docker-local/")) for name in names)
        assert not any("__pycache__" in name or name.endswith((".pyc", "-export.sql", ".pdf")) for name in names)


def test_public_package_check_rejects_a_known_environment_secret(tmp_path, monkeypatch):
    secret = "test-" + "credential-" + "do-not-publish"
    monkeypatch.setenv("PART1_DB_PASSWORD", secret)
    source = tmp_path / "bad.py"
    source.write_text(f"password = {secret!r}", encoding="utf-8")
    with pytest.raises(ValueError, match="Credential check failed"):
        verify_sources([source], root=tmp_path)
