"""Shared environment utilities for loading credentials from ~/.env files."""

import os


def load_env_file() -> None:
    """Load environment variables from ~/.env file.

    Reads key=value pairs, skips comments and blank lines.
    Uses setdefault so existing environment variables are not overwritten.
    """
    env_file = os.path.expanduser("~/.env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
