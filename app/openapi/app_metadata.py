"""Static application metadata surfaced in the OpenAPI document.

Per project convention, fixed values live in a named config object rather than
as bare module-level constants, so the API's title, description, and the name
of the installed distribution are declared in exactly one place. The version is
**not** hardcoded: it is read from the installed package metadata (the
``[project]`` table in ``pyproject.toml``) so the ``/openapi.json`` document
always reports the release actually deployed.
"""

import importlib.metadata


class AppMetadata:
    """Title, description, and installed version of the LAVS distribution."""

    TITLE: str = "LAVS"
    DESCRIPTION: str = (
        "The lowercase acronym versioning system — tracks products, their "
        "components, and immutable component versions; cuts releases with "
        "frozen manifests; and streams live timeline events over SSE. "
        "Authentication is pluggable per deployment: browser session cookie "
        "(password login) and/or headless `X-API-Key` header."
    )
    PACKAGE_NAME: str = "lavs"
    FALLBACK_VERSION: str = "0.0.0"

    @classmethod
    def version(cls) -> str:
        """Return the installed version of the ``lavs`` distribution.

        Returns:
            The version string from the installed package metadata, or the
            fallback version when the distribution is not installed (for
            example when the app is imported straight from a source checkout).
        """
        try:
            return importlib.metadata.version(cls.PACKAGE_NAME)
        except importlib.metadata.PackageNotFoundError:
            return cls.FALLBACK_VERSION
