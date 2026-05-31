from __future__ import annotations


class HermesError(Exception):
    """Base exception for user-facing Hermes failures."""


class ConfigError(HermesError):
    """Raised when Hermes configuration is invalid."""


class UsageError(HermesError):
    """Raised when command arguments are valid syntax but unsafe or incomplete."""


class ExternalCommandError(HermesError):
    """Raised when a delegated system command fails."""
