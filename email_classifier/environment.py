"""Load project-local environment values without replacing process settings."""

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / '.env'
_loaded_signature = None


def load_local_environment():
    """Load .env values, filling unset or blank variables only.

    A non-empty value supplied by the process environment takes precedence.
    Re-checking the file lets a running local Django server pick up .env values
    if the file is added after startup. Existing non-empty process values remain
    authoritative.
    """
    global _loaded_signature

    if not ENV_FILE.is_file():
        return

    stat = ENV_FILE.stat()
    signature = (stat.st_mtime_ns, stat.st_size)
    if signature == _loaded_signature:
        return

    file_values = dotenv_values(dotenv_path=ENV_FILE)
    load_dotenv(dotenv_path=ENV_FILE, override=False)

    # python-dotenv treats an explicitly blank inherited variable as present.
    # Fill those blanks from .env while keeping non-empty process values intact.
    for name, value in file_values.items():
        if value and not os.environ.get(name):
            os.environ[name] = value

    _loaded_signature = signature
