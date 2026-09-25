import hashlib
import io
import os

import pytest

import updater

REPO = "canadianproducer/holos"
BASE = f"https://github.com/{REPO}/releases/download"


def release(tag="v9.9.9", digest=None, url=None, **extra):
    asset = {
        "name": "Holos-Setup-9.9.9.exe",
        "size": 3,
        "browser_download_url": url or f"{BASE}/{tag}/Holos-Setup-9.9.9.exe",
    }
    if digest:
        asset["digest"] = digest
    return {"tag_name": tag, "html_url": "page", "body": "notes", "assets": [asset], **extra}


@pytest.mark.parametrize(
    ("a", "b"),
    [("v0.10.0", "0.9.9"), ("1.0.0", "0.99.99"), ("v0.3.1", "0.3.0"), ("2.0", "1.9.9")],
)
def test_parse_version_orders_numerically(a, b):
    assert updater.parse_version(a) > updater.parse_version(b)


def test_no_update_when_not_newer():
    assert updater.parse_release(release("v0.3.0"), REPO, current="0.3.0") is None
    assert updater.parse_release(release("v0.2.9"), REPO, current="0.3.0") is None


@pytest.mark.parametrize("flag", ["draft", "prerelease"])
def test_drafts_and_prereleases_are_ignored(flag):
    assert updater.parse_release(release(**{flag: True}), REPO, current="0.1.0") is None


def test_digest_is_used():
    sha = "a" * 64
    info = updater.parse_release(release(digest=f"sha256:{sha}"), REPO, current="0.1.0")
    assert info["sha256"] == sha
    assert info["asset"].startswith(BASE)


def test_invalid_digest_is_rejected():
    info = updater.parse_release(release(digest="sha256:nothex"), REPO, current="0.1.0")
    assert info["sha256"] is None


def test_foreign_download_url_is_ignored():
    info = updater.parse_release(release(url="https://evil.example/Holos-Setup.exe"), REPO, current="0.1.0")
    assert info["asset"] is None


def test_parse_sums():
    sha = "b" * 64
    text = f"{'c' * 64}  other.exe\n{sha} *Holos-Setup-9.9.9.exe\n"
    assert updater.parse_sums(text, "Holos-Setup-9.9.9.exe") == sha
    assert updater.parse_sums(text, "missing.exe") is None


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


@pytest.fixture
def serve(monkeypatch, tmp_path):
    monkeypatch.setattr(updater.tempfile, "gettempdir", lambda: str(tmp_path))

    def _serve(payload: bytes):
        monkeypatch.setattr(updater, "_get", lambda url, timeout, accept=None: FakeResponse(payload))

    return _serve


def info_for(payload: bytes, **over):
    return {
        "asset": f"{BASE}/v9.9.9/x.exe",
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        **over,
    }


def test_download_verifies_and_returns_file(serve, tmp_path):
    serve(b"abc")
    path = updater.download(info_for(b"abc"))
    assert open(path, "rb").read() == b"abc"
    assert not os.path.exists(path + ".part")


def test_download_rejects_wrong_hash(serve, tmp_path):
    serve(b"evil")
    with pytest.raises(updater.UpdateError):
        updater.download(info_for(b"evil", sha256="0" * 64))
    assert os.listdir(tmp_path) == []


def test_download_rejects_truncated_file(serve, tmp_path):
    serve(b"ab")
    with pytest.raises(updater.UpdateError):
        updater.download(info_for(b"ab", size=10))
    assert os.listdir(tmp_path) == []


def test_download_requires_checksum(serve):
    serve(b"abc")
    with pytest.raises(updater.UpdateError):
        updater.download(info_for(b"abc", sha256=None))


def test_only_https(monkeypatch):
    with pytest.raises(updater.UpdateError):
        updater._get("http://github.com/x", 1)
