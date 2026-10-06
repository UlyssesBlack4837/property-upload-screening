import base64
import json
from unittest.mock import patch

from property_screening import InfraiImageClient, screen_caption


def test_sensitive_tenant_caption_is_held_before_publish():
    result = screen_caption("Lease scan with tenant social security number")
    assert result.publish is False
    assert "sensitive term" in result.reason


def test_maintenance_caption_can_publish():
    result = screen_caption("Dripping faucet in unit 4B")
    assert result.publish is True
    assert result.reason == "caption passed privacy review"


def test_upload_sends_json_with_base64_file():
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def read(self):
            return b'{"ok": true, "data": {"id": "image-1"}}'

    with patch("property_screening.urlopen", return_value=Response()) as send:
        result = InfraiImageClient(api_key="test-key").upload(b"\x00\xff", "test.png")

    request = send.call_args.args[0]
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == {
        "file": base64.b64encode(b"\x00\xff").decode("ascii"),
        "filename": "test.png",
    }
    assert result == {"id": "image-1"}
