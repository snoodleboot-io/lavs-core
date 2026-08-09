"""A pydantic-friendly ULID identifier type.

ULIDs are used as the primary-key/foreign-key identifier for every resource in
LAVS (products, components, versions). They are stored and transported as their
26-character Crockford base32 string form so the same value round-trips cleanly
through DuckDB ``VARCHAR`` columns and JSON bodies.
"""

from typing import Annotated

from pydantic import AfterValidator
from ulid import ULID


def new_ulid() -> str:
    """Generate a fresh ULID rendered as its canonical 26-character string.

    Returns:
        str: A newly minted ULID in Crockford base32 form.
    """
    return str(ULID())


def validate_ulid(field_value: str) -> str:
    """Validate that a string is a well-formed ULID.

    Delegates the format check (26-character length and the Crockford base32
    alphabet) to :meth:`ulid.ULID.from_str`, then returns the original string so
    the canonical text form is preserved.

    Args:
        field_value: The candidate ULID string.

    Returns:
        str: The validated ULID string, unchanged.

    Raises:
        ValueError: When the value is not a valid ULID string.
    """
    ULID.from_str(field_value)
    return field_value


UlidId = Annotated[str, AfterValidator(validate_ulid)]
"""An annotated ``str`` that accepts only a valid 26-character ULID string."""
