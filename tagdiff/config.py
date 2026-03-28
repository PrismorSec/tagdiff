import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CACHE_DIR = Path(os.getenv("TAGDIFF_CACHE_DIR", Path.home() / ".cache" / "tagdiff"))
DEFAULT_CACHE_TTL = 3600  # 1 hour
DEFAULT_MODEL = os.getenv("TAGDIFF_MODEL", "gpt-5-nano")
