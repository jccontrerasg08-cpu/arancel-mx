"""Runtime configuration shared by the operational Vercel functions."""

from __future__ import annotations

import os
from collections.abc import Mapping


DATABASE_URL_ENVIRONMENT_KEYS = (
    "ARANCEL_MX_DATABASE_URL",
    "ARANCEL_MX_DATABASE_DATABASE_URL",
)


def operational_database_url(environ: Mapping[str, str] | None = None) -> str | None:
    """Return the first configured operational database URL without exposing it.

    ``ARANCEL_MX_DATABASE_URL`` is the project-level canonical name. The second
    name is supplied by Vercel's managed Neon integration and is retained as a
    compatibility path so deployments can use the integration without copying
    database secrets into a duplicate project variable.
    """

    source = os.environ if environ is None else environ
    for environment_key in DATABASE_URL_ENVIRONMENT_KEYS:
        value = source.get(environment_key, "").strip()
        if value:
            return value
    return None
