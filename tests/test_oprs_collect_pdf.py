"""OPRS collector PDF-endpoint tests.

Covers the Phase 01.5 additions to datasets/collect_oprs.py:
    - URL builders for prc.pdf / ch75.pdf / taxlist_<year>.pdf
    - PDF response validation (%PDF marker + size floor)
    - tmp-PDF href extraction regex
    - Two-request session-bound flow with prc-only HTTP-header strip (D-27/D-28)
    - fetch_component 3-tuple contract for the cached path

All tests are pure-Python (no live network); the two-step flow is exercised
with a fake session whose .get() returns stub responses popped from a list.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from datasets.collect_oprs import (
    COMPONENT_CH75,
    COMPONENT_PRC,
    _PDF_HREF_RE,
    _build_url,
    _fetch_pdf_two_step,
    _validate,
    fetch_component,
    taxlist_component_name,
)


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------

def test_build_url_prc():
    # PDF endpoints use h00/h01/h02/ccdd (NOT l02). Verified against live OPRS:
    # the l02 form returns a generic stub PDF; h00/h01 returns parcel-specific.
    url = _build_url("prc.pdf", "77", "80", "", None)
    assert "prc.cgi" in url
    assert "ccdd=1314" in url
    assert "h00=77" in url and "h01=80" in url and "h02=" in url


def test_build_url_ch75():
    url = _build_url("ch75.pdf", "77", "80", "", None)
    assert "ch75.cgi" in url
    assert "ccdd=1314" in url
    assert "h00=77" in url and "h01=80" in url
    assert "i24=2" in url


def test_build_url_taxlist_extracts_year():
    url = _build_url("taxlist_2026.pdf", "3", "33", "", None)
    assert "taxlist.cgi" in url
    assert "year=2026" in url
    assert "ccdd=1314" in url
    assert "h00=3" in url and "h01=33" in url


def test_build_url_taxlist_unknown_year_raises():
    with pytest.raises(ValueError):
        _build_url("taxlist_abcd.pdf", "3", "33", "", None)


# ---------------------------------------------------------------------------
# Validators (PDF branch)
# ---------------------------------------------------------------------------

def test_validate_pdf_rejects_html():
    body = b"<html>not a pdf</html>" + b"x" * 600
    ok, status = _validate("prc.pdf", body, "77", "80")
    assert ok is False
    assert status == "no_pdf_marker"


def test_validate_pdf_accepts_marker():
    body = b"%PDF-1.4\n" + b"x" * 600
    ok, status = _validate("prc.pdf", body, "77", "80")
    assert ok is True
    assert status == "ok"


def test_validate_pdf_rejects_too_small():
    body = b"%PDF-1.4\n"  # only 9 bytes
    ok, status = _validate("prc.pdf", body, "77", "80")
    assert ok is False
    assert status.startswith("too_small:")


# ---------------------------------------------------------------------------
# tmp-PDF href regex
# ---------------------------------------------------------------------------

def test_pdf_href_re_extracts():
    html = '<html><body><a href="/tmp/xyz123.pdf">Download</a></body></html>'
    m = _PDF_HREF_RE.search(html)
    assert m is not None
    assert m.group(1) == "/tmp/xyz123.pdf"


def test_pdf_href_re_extracts_relative_no_leading_slash():
    html = "<a href='tmp/abc.pdf'>x</a>"
    m = _PDF_HREF_RE.search(html)
    assert m is not None
    assert m.group(1) == "tmp/abc.pdf"


def test_pdf_href_re_extracts_unquoted_href_real_prc_shape():
    # Real prc.cgi response shape: unquoted href in an <a> tag.
    html = "<a href=../tmp/prc-1314-30-1--10928.pdf>Click Here</a>"
    m = _PDF_HREF_RE.search(html)
    assert m is not None
    assert m.group(1) == "../tmp/prc-1314-30-1--10928.pdf"


def test_pdf_href_re_extracts_frame_src_real_ch75_shape():
    # Real ch75.cgi/taxlist.cgi response shape: <frame src=../tmp/x.pdf> (no quotes).
    html = "<frame name=FrmR src=../tmp/ch75.10917.pdf resize>"
    m = _PDF_HREF_RE.search(html)
    assert m is not None
    assert m.group(1) == "../tmp/ch75.10917.pdf"


# ---------------------------------------------------------------------------
# Two-step PDF fetch with header strip
# ---------------------------------------------------------------------------

class _StubResp:
    def __init__(self, status_code: int, content: bytes):
        self.status_code = status_code
        self.content = content


class _FakeSession:
    """Session double whose .get() pops responses from a queue."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[str] = []

    def get(self, url, timeout=30):
        self.calls.append(url)
        if not self._responses:
            raise RuntimeError(f"no stubbed response for {url}")
        return self._responses.pop(0)


def test_fetch_pdf_two_step_strips_prc_header():
    cgi_html = b'<html><a href="/tmp/abc.pdf">d</a></html>'
    # Upstream prepends a literal HTTP envelope before the real PDF body (D-28)
    polluted_pdf = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n%PDF-1.4\n" + b"x" * 600
    sess = _FakeSession([_StubResp(200, cgi_html), _StubResp(200, polluted_pdf)])

    status, body, made = _fetch_pdf_two_step(
        sess,  # type: ignore[arg-type]
        "https://tax1.co.monmouth.nj.us/cgi-bin/prc.cgi?district=1314&l02=...",
        COMPONENT_PRC,
    )
    assert status == 200
    assert made == 2
    assert body is not None
    assert body.startswith(b"%PDF-1.4")
    # Two requests went out, second resolved against TAX1_HOST
    assert len(sess.calls) == 2
    assert sess.calls[1].endswith("/tmp/abc.pdf")


def test_fetch_pdf_two_step_no_strip_for_ch75():
    cgi_html = b'<html><a href="/tmp/clean.pdf">d</a></html>'
    clean_pdf = b"%PDF-1.7\n" + b"y" * 800
    sess = _FakeSession([_StubResp(200, cgi_html), _StubResp(200, clean_pdf)])

    status, body, made = _fetch_pdf_two_step(
        sess,  # type: ignore[arg-type]
        "https://tax1.co.monmouth.nj.us/cgi-bin/ch75.cgi?district=1314&l02=...",
        COMPONENT_CH75,
    )
    assert status == 200
    assert made == 2
    assert body == clean_pdf  # not modified


def test_fetch_pdf_two_step_missing_href_returns_one_request():
    cgi_html = b"<html><body>no link here</body></html>"
    sess = _FakeSession([_StubResp(200, cgi_html)])

    status, body, made = _fetch_pdf_two_step(
        sess,  # type: ignore[arg-type]
        "https://tax1.co.monmouth.nj.us/cgi-bin/prc.cgi",
        COMPONENT_PRC,
    )
    assert status == 200
    assert body is None
    assert made == 1


# ---------------------------------------------------------------------------
# fetch_component 3-tuple contract
# ---------------------------------------------------------------------------

def test_fetch_component_returns_tuple_3_for_cached(tmp_path: Path):
    pin = "1314_77_80"
    parcel_dir = tmp_path / pin
    parcel_dir.mkdir()
    # Plant a "cached" m4.html (>200 bytes per is_cached threshold)
    (parcel_dir / "m4.html").write_bytes(b"<html>" + b"x" * 600 + b"</html>")

    result = fetch_component(
        session=None,  # type: ignore[arg-type]  — cached path doesn't touch session
        pams_pin=pin,
        component="m4.html",
        output_root=tmp_path,
        max_retries=1,
    )
    assert isinstance(result, tuple) and len(result) == 3
    ok, status, made = result
    assert ok is True
    assert status == "cached"
    assert made == 0
