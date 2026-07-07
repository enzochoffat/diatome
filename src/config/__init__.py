"""Compatibility package for configuration imports.

This package re-exports the central configuration constants from
src.core.config so legacy imports like ``from src import config`` keep
working.
"""

from src.core.config import *  # noqa: F401,F403
