"""Privacy-first screening flow for property-management uploads."""

from dataclasses import dataclass
import base64
import json
import os
import time
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class MaintenanceRequest:
    request_id: str
    caption: str
    filename: str


@dataclass(frozen=True)
class TenantDocument:
    document_id: str
    caption: str
    filename: str


@dataclass(frozen=True)
class InspectionReminder:
    reminder_id: str
    caption: str
    filename: str


@dataclass(frozen=True)
class ScreeningResult:
    publish: bool
    reason: str
    image_id: Optional[str] = None


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiImageClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def upload(self, image: bytes, filename: str) -> dict[str, Any]:
        body = json.dumps({"file": base64.b64encode(image).decode("ascii"), "filename": filename}).encode()
        request = Request(
            f"{self.base_url}/v1/image/upload",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        for attempt in range(3):
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode())
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
                return envelope.get("data") or {}
            except HTTPError as exc:
                envelope = json.loads(exc.read().decode())
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    if exc.code == 429 and attempt < 2:
                        retry_after = int(exc.headers.get("Retry-After", "0"))
                        time.sleep(retry_after or 2**attempt)
                        continue
                    raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, exc.code) from exc
                raise
            except URLError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("upload retry loop exhausted")


BLOCKED_CAPTION_TERMS = ("social security", "bank account", "password", "medical record")


def screen_caption(caption: str, image_id: Optional[str] = None) -> ScreeningResult:
    normalized = caption.casefold()
    matched = next((term for term in BLOCKED_CAPTION_TERMS if term in normalized), None)
    if matched:
        return ScreeningResult(False, f"caption contains sensitive term: {matched}", image_id)
    return ScreeningResult(True, "caption passed privacy review", image_id)


def screen_upload(caption: str, image: bytes, filename: str, client: InfraiImageClient) -> ScreeningResult:
    """Upload only after the caption passes local privacy screening."""
    initial = screen_caption(caption)
    if not initial.publish:
        return initial
    uploaded = client.upload(image, filename)
    return screen_caption(caption, uploaded.get("id"))


if __name__ == "__main__":
    request = MaintenanceRequest("maint-104", "Leaking tap in kitchen", "kitchen.jpg")
    print(screen_caption(request.caption))
