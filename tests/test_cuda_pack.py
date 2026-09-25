import io

import pytest

import cuda_pack


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def test_pinned_packages_are_well_formed():
    for _pkg, ver, inner, size, sha256, url in cuda_pack.PACKAGES:
        assert url.startswith("https://files.pythonhosted.org/")
        assert ver in url and url.endswith("win_amd64.whl")
        assert len(sha256) == 64 and size > 0 and inner.endswith("/bin/")


def test_download_rejects_bad_hash(monkeypatch, tmp_path):
    monkeypatch.setattr(cuda_pack.urllib.request, "urlopen", lambda url, timeout: FakeResponse(b"xyz"))
    dest = tmp_path / "w.whl"
    with pytest.raises(RuntimeError):
        cuda_pack._download("https://files.pythonhosted.org/w.whl", 3, "0" * 64, dest, lambda n: None)
    assert not dest.exists()
