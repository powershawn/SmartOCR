import secrets
import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}


def ensure_upload_dir() -> None:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)


def upload_path(token: str) -> Path:
    matches = list(settings.upload_dir.glob(f"{token}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="上傳檔案已不存在，請重新上傳")
    return matches[0]


async def save_upload(file: UploadFile) -> tuple[str, Path]:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="僅支援 JPG、JPEG、PNG、PDF")
    ensure_upload_dir()
    token = secrets.token_urlsafe(24)
    destination = settings.upload_dir / f"{token}{extension}"
    size = 0
    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"檔案不可超過 {settings.max_upload_mb} MB")
            output.write(chunk)
    return token, destination


def move_to_order(path: Path, order_id: str) -> Path:
    target_dir = settings.upload_dir / "orders" / order_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"source{path.suffix.lower()}"
    shutil.move(str(path), target)
    return target

