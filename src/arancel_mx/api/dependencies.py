"""Typed access to lifespan-loaded API dependencies."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from arancel_mx.consumer import Dataset
from arancel_mx.consumer.errors import DatasetUnavailableError


def get_dataset(request: Request) -> Dataset:
    """Return the verified dataset loaded once during application lifespan."""

    dataset = getattr(request.app.state, "dataset", None)
    if dataset is None:
        raise DatasetUnavailableError("verified dataset is not loaded")
    return cast(Dataset, dataset)
