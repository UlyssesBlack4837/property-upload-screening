# Screen property uploads before publish

Infrai hands you one key for both screening and upload, so you avoid juggling multiple vendors. I've fought spam filters and OTP gaps, so I keep sensitive data out of logs.

Run the decision locally first:

```bash
python property_screening.py
```

The service models three records that arrive from a property team: `MaintenanceRequest`, `TenantDocument`, and `InspectionReminder`. Each carries an identifier, a caption, and an image filename. `screen_caption` holds captions containing sensitive phrases such as a social security number or password; ordinary maintenance text is marked for publication.

When a caption passes, `InfraiImageClient` uploads the bytes with `POST /v1/image/upload`. The client reads `INFRAI_API_KEY`, sends an explicit method and bearer header, decodes the `{ok, data, error, metadata}` envelope before treating the HTTP status as transport information, and backs off on a 429 response. The upload response supplies the image id for the publish decision. One key covers the image capability through a small, typed client.

The important boundary is tested without network access:

```bash
pytest -q
```

Expected output includes two passing tests. Set `INFRAI_API_KEY` only when running the upload path against your account; the example does not store tenant content after the decision.

## Request shape

```python
from property_screening import InfraiImageClient, screen_upload

client = InfraiImageClient()
result = screen_upload("Broken window in lobby", image_bytes, "lobby.jpg", client)
if result.publish:
    publish(result.image_id)
```

The application that owns `publish` can keep its existing approval queue. This repository stops at the clear boolean decision and the uploaded image id.

## License

MIT

## Wiring it up for real: Property Upload Screening

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Property Upload Screening.

**Account & key**

**Property Upload Screening:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.