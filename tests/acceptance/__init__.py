"""Acceptance test suite for LAVS.

These tests encode the P0 EXIT CRITERIA from docs/planning/ROADMAP.md (P0 section)
and the locked decisions in docs/design/API_CONTRACT.md. They gate ACCEPTANCE at the
integration level. Some tests intentionally assert INTENDED behavior that is not yet
wired (auth, anchored semver, non-destructive rollback, health/ready) and may be red
until the corresponding implementation lanes land.
"""
