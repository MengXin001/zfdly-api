import re
from pathlib import Path

from core.config import settings

_STORED_UPLOAD_URL = re.compile(
    r"^/uploads/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.(jpg|png|webp)$"
)


def upload_path_from_url(url: str) -> Path | None:
    match = _STORED_UPLOAD_URL.fullmatch(url)
    if match is None:
        return None
    return Path(settings.UPLOAD_DIR) / f"{match.group(1)}.{match.group(2)}"
