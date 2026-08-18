from __future__ import annotations


def test_discover_official_pdf_links_keeps_only_allowlisted_https_pdf_documents():
    from arancel_mx.sources.dof_pdf import discover_official_pdf_links

    html = """
    <main>
      <a href="/2026/08/ligie-reform.pdf">Decreto LIGIE</a>
      <a href="https://www.dof.gob.mx/nico-amendment.PDF?edition=morning">NICO</a>
      <a href="https://cdn.example.invalid/forged.pdf">Ignore me</a>
      <a href="http://dof.gob.mx/insecure.pdf">Ignore me too</a>
      <a href="/2026/08/notes.html">Not a PDF</a>
      <a href="/2026/08/ligie-reform.pdf">Duplicate</a>
    </main>
    """

    assert discover_official_pdf_links(
        html,
        page_url="https://www.dof.gob.mx/2026/08/18",
        allowed_hosts=("dof.gob.mx", "www.dof.gob.mx"),
    ) == (
        "https://www.dof.gob.mx/2026/08/ligie-reform.pdf",
        "https://www.dof.gob.mx/nico-amendment.PDF?edition=morning",
    )
