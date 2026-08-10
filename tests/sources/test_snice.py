from arancel_mx.sources.snice import discover_snice_documents


class Response:
    def __init__(self, url, text):
        self.url = url
        self.text = text

    def raise_for_status(self):
        return None


class Client:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url, timeout):
        assert timeout == 10
        return Response(url, self.pages[url])


def test_discovery_accepts_only_official_documents_and_builds_tasks():
    ligie_url = "https://www.snice.gob.mx/ligie"
    nico_url = "https://www.snice.gob.mx/nico"
    modification_url = "https://www.snice.gob.mx/modificaciones"
    pages = {
        ligie_url: """
            <a href='/~oracle/SNICE_DOCS/LIGIE2022.xlsx'>LIGIE 2022 Excel</a>
            <a href='https://evil.example/ligie.xlsx'>Copia</a>
        """,
        nico_url: "<a href='/~oracle/SNICE_DOCS/NICO2022.xlsx'>NICO 2022 Excel</a>",
        modification_url: """
            <a href='https://www.dof.gob.mx/nota_detalle.php?codigo=123'>DOF modificación</a>
            <a href='/~oracle/SNICE_DOCS/MODLIGIE2026.xlsx'>Cambios Excel 23 abril 2026</a>
        """,
    }

    tasks = discover_snice_documents(
        Client(pages), ligie_url, nico_url, modification_url, timeout_s=10
    )

    assert [task.url for task in tasks] == [
        "https://www.snice.gob.mx/~oracle/SNICE_DOCS/LIGIE2022.xlsx",
        "https://www.snice.gob.mx/~oracle/SNICE_DOCS/NICO2022.xlsx",
        "https://www.dof.gob.mx/nota_detalle.php?codigo=123",
        "https://www.snice.gob.mx/~oracle/SNICE_DOCS/MODLIGIE2026.xlsx",
    ]
    assert [task.kind for task in tasks] == [
        "ligie",
        "nico",
        "modification",
        "modification",
    ]
    assert [task.relative_path for task in tasks] == [
        "ligie-001.xlsx",
        "nico-001.xlsx",
        "modification-001.html",
        "modification-002.xlsx",
    ]
    assert all(task.provenance["source_url"] == task.url for task in tasks)
