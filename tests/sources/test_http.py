from datetime import timezone

import pytest

from arancel_mx.sources.http import decode_fetched_text, fetch_official_document


class Response:
    def __init__(
        self,
        url,
        content=b"abc",
        content_type="application/pdf",
        content_length=None,
    ):
        self.url = url
        self.content = content
        self.headers = {"Content-Type": content_type}
        self.headers["Content-Length"] = str(
            len(content) if content_length is None else content_length
        )

    def raise_for_status(self):
        return None


class Session:
    def __init__(self, response):
        self.response = response

    def get(self, url, timeout):
        return self.response


def test_redirect_outside_registered_host_is_rejected():
    with pytest.raises(ValueError, match="not allowed"):
        fetch_official_document(
            Session(Response("https://example.com/file.pdf")),
            "https://www.snice.gob.mx/file.pdf",
            ("www.snice.gob.mx", "snice.gob.mx"),
            ("application/pdf",),
        )


def test_registered_content_type_with_charset_is_accepted():
    fetched = fetch_official_document(
        Session(
            Response(
                "https://www.snice.gob.mx/file.pdf",
                content_type="application/pdf; charset=binary",
            )
        ),
        "https://www.snice.gob.mx/file.pdf",
        ("www.snice.gob.mx", "snice.gob.mx"),
        ("application/pdf",),
    )

    assert fetched.content == b"abc"
    assert fetched.media_type == "application/pdf"
    assert fetched.retrieved_at.tzinfo is timezone.utc


def test_text_decoder_honors_declared_legacy_charset():
    text = "Última reforma publicada"
    fetched = fetch_official_document(
        Session(
            Response(
                "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm",
                content=text.encode("iso-8859-1"),
                content_type="text/html; charset=iso-8859-1",
            )
        ),
        "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm",
        ("www.diputados.gob.mx", "diputados.gob.mx"),
        ("text/html",),
    )

    assert fetched.charset == "iso-8859-1"
    assert decode_fetched_text(fetched) == text


def test_text_decoder_falls_back_to_windows_1252_for_legacy_html_without_charset():
    text = "Reforma – vigente"
    fetched = fetch_official_document(
        Session(
            Response(
                "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm",
                content=text.encode("cp1252"),
                content_type="text/html",
            )
        ),
        "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm",
        ("www.diputados.gob.mx", "diputados.gob.mx"),
        ("text/html",),
    )

    assert fetched.charset is None
    assert decode_fetched_text(fetched) == text


def test_declared_size_over_limit_is_rejected():
    with pytest.raises(ValueError, match="size"):
        fetch_official_document(
            Session(Response("https://www.snice.gob.mx/file.pdf", content_length=4)),
            "https://www.snice.gob.mx/file.pdf",
            ("www.snice.gob.mx", "snice.gob.mx"),
            ("application/pdf",),
            max_bytes=3,
        )


def test_actual_size_over_limit_is_rejected_even_when_header_is_small():
    with pytest.raises(ValueError, match="size"):
        fetch_official_document(
            Session(
                Response(
                    "https://www.snice.gob.mx/file.pdf",
                    content=b"abcd",
                    content_length=3,
                )
            ),
            "https://www.snice.gob.mx/file.pdf",
            ("www.snice.gob.mx", "snice.gob.mx"),
            ("application/pdf",),
            max_bytes=3,
        )


def test_octet_stream_is_accepted_only_for_registered_file_extension():
    xlsx_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    fetched = fetch_official_document(
        Session(
            Response(
                "https://www.snice.gob.mx/FRACCIONESARANCELARIAS.XLSX",
                content_type="application/octet-stream",
            )
        ),
        "https://www.snice.gob.mx/FRACCIONESARANCELARIAS.XLSX",
        ("www.snice.gob.mx", "snice.gob.mx"),
        (xlsx_type,),
    )

    assert fetched.media_type == xlsx_type

    with pytest.raises(ValueError, match="media type"):
        fetch_official_document(
            Session(
                Response(
                    "https://www.snice.gob.mx/file.bin",
                    content_type="application/octet-stream",
                )
            ),
            "https://www.snice.gob.mx/file.bin",
            ("www.snice.gob.mx", "snice.gob.mx"),
            (xlsx_type,),
        )
