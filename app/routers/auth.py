"""Router shell for the ``/auth`` resource.

A deliberate shell carrying only the prefix and tag — the password-auth lanes
add the routes (R1: ``/auth/signup`` + ``/auth/verify``; R2: ``/auth/login`` +
``/auth/logout`` + ``/auth/me``). See ``docs/design/API_CONTRACT.md`` §2.

Critically, this router does **not** declare the ``require_principal``
dependency: the auth routes establish a principal, so they must be reachable
without one already present. (``/auth/me`` enforces authentication itself.)
"""

from fastapi import APIRouter

router = APIRouter(tags=["auth"], prefix="/auth")
