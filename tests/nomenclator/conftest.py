"""Shared pytest configuration for the nomenclator test suite."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_HS_DEPS = (
    "dspy",
    "bm25s",
    "httpx",
    "bs4",
    "pypdf",
    "model2vec",
    "vicinity",
    "rich",
)


def _hs_extra_missing() -> bool:
    import importlib.util

    return any(importlib.util.find_spec(name) is None for name in _HS_DEPS)


def pytest_ignore_collect(collection_path: Any, config: pytest.Config) -> bool:
    """Skip upstream nomenclator tests unless `arancel-mx[hs]` is installed."""
    return _hs_extra_missing()


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: tests that call the live WCO nomenclature source",
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--nomenclator-live",
        action="store_true",
        default=False,
        help="Run nomenclator integration tests that hit WCO and OpenAI",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Keep live WCO/OpenAI tests off the default suite (same as upstream CI)."""
    if config.getoption("nomenclator_live", default=False):
        return
    skip_live = pytest.mark.skip(reason="live WCO/OpenAI; pass --nomenclator-live")
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip_live)


@pytest.fixture
def nomenclature_client() -> Iterator[Any]:
    """Provide a live nomenclature client."""
    from nomenclator.nomenclature.client import NomenclatureClient

    with NomenclatureClient() as client:
        yield client


@pytest.fixture
def general_rules() -> Any:
    """Compact fake GIR payload for classification pipeline tests."""
    from nomenclator.nomenclature.rules import HSGeneralRule, HSGeneralRules
    from nomenclator.nomenclature.tree import HSDocumentRef

    return HSGeneralRules(
        title="General Rules for the interpretation of the Harmonized System",
        document=HSDocumentRef(
            title="General Rules",
            ref="0001-2202E GIR",
        ),
        rules=[
            HSGeneralRule(
                rule="1",
                text=(
                    "Classification shall be determined according to the "
                    "terms of the headings."
                ),
            ),
            HSGeneralRule(
                rule="2(a)",
                text=(
                    "Any reference to an article includes incomplete or "
                    "unfinished articles."
                ),
            ),
        ],
    )


@pytest.fixture
def agent(general_rules: Any) -> Iterator[Any]:
    """Create an agent with mocked dependencies."""
    from nomenclator.agent import HSClassificationAgent

    client = MagicMock()
    client.get_general_rules.return_value = general_rules

    agent = HSClassificationAgent.__new__(HSClassificationAgent)

    agent._client = client
    agent._embedding_model = "test-model"
    agent._max_retrieved_chapters = 5
    agent._max_research_chapters = 3
    agent._max_classification_chunks = 20

    agent._product_analyst = MagicMock()
    agent._research_analyst = MagicMock()
    agent._classification_analyst = MagicMock()

    with patch("nomenclator.agent.ensure_dspy_lm"):
        yield agent


@pytest.fixture
def heading_mock():
    """Factory for mocked HSHeading objects."""

    def factory(heading_dict: dict) -> MagicMock:
        heading = MagicMock()
        heading.to_dict.return_value = heading_dict
        return heading

    return factory


@pytest.fixture
def chapter_mock():
    """Factory for mocked HSChapter objects."""

    def factory(
        *,
        chapter_number: int = 85,
        title: str = "Electrical machinery and equipment",
        ref: str = "8501-2022E",
        url: str = (
            "https://www.wcoomd.org/-/media/wco/public/global/pdf/topics/"
            "nomenclature/instruments-and-tools/hs-nomenclature-2022/2022/"
            "8501-2022e.pdf?la=en"
        ),
        notes: list | None = None,
    ) -> MagicMock:
        chapter = MagicMock()
        chapter.chapter_number = chapter_number
        chapter.title = title
        chapter.document.ref = ref
        chapter.document.url = url
        chapter.notes = notes if notes is not None else []
        chapter.headings = []
        return chapter

    return factory


@pytest.fixture
def patch_candidate_chapters():
    """Factory for patching _retrieve_chapters()."""
    from nomenclator.agent import HSClassificationAgent

    def factory(retrieved: list):
        return patch.object(
            HSClassificationAgent,
            "_retrieve_chapters",
            return_value=retrieved,
        )

    return factory


@pytest.fixture
def patch_headings():
    """Factory for patching _retrieve_headings()."""
    from nomenclator.agent import HSClassificationAgent

    def factory(headings_by_chapter: dict[int, list[MagicMock]]):
        return patch.object(
            HSClassificationAgent,
            "_retrieve_headings",
            return_value=headings_by_chapter,
        )

    return factory


@pytest.fixture
def search_result(heading_mock):
    """Factory for mocked SearchResult objects."""

    def factory(
        chunk_id: str,
        chapter_number: int,
        heading_dict: dict,
    ) -> MagicMock:
        heading = heading_mock(heading_dict)

        document = MagicMock()
        document.id = chunk_id
        document.payload = heading

        result = MagicMock()
        result.document = document

        return result

    return factory
