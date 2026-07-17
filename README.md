# Outbound Webhooks

A Home Assistant integration that adds a **Send request** action to the automation builder, so you can fire configured HTTP requests (webhooks) to external APIs as a drag/drop step - no YAML, no shell, no `rest_command`.

It works like a `curl`: you pick a method, set headers and auth, add a body, and optionally capture the response.

> Early development. The generic **Send request** action works today. Saved **presets** (pick a named webhook from a dropdown and pass data) are coming next.

## Install

**HACS (custom repository)**

1. HACS → three-dot menu → **Custom repositories**.
2. Add `https://github.com/aaronfagan/ha-outbound-webhooks`, category **Integration**.
3. Install **Outbound Webhooks**, then restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → Outbound Webhooks**.

## Use it in an automation

Add an action, choose **Outbound Webhooks: Send request**, and fill in the fields:

```yaml
actions:
  - action: outbound_webhooks.send
    data:
      url: "https://api.example.com/v1/events"
      method: POST
      auth_type: bearer
      token: !secret my_api_token
      content_type: application/json
      payload: '{"event": "{{ trigger.id }}", "at": "{{ now().isoformat() }}"}'
    response_variable: result
  - if: "{{ result.status != 200 }}"
    then:
      - action: persistent_notification.create
        data:
          message: "Webhook failed: {{ result.status }}"
```

The fields render as form inputs in the visual editor - you never have to touch YAML.

### Fields

| Field | What it does |
|---|---|
| **URL** | Where to send the request (templates allowed) |
| **Method** | GET / POST / PUT / PATCH / DELETE |
| **Headers** | Extra request headers |
| **Authentication** | None, Bearer, X-API-Key, or Basic |
| **Payload** | The request body (templates allowed) |
| **Content type** | Content-Type for the body |
| **Timeout** | Seconds before giving up (default 10) |
| **Verify SSL** | Verify the server's TLS certificate (default on) |
| **Follow redirects** | Follow HTTP redirects (default on) |

### Response

When you set `response_variable`, the action returns:

- `status` - the HTTP status code
- `headers` - the response headers
- `body` - the response body as text

## License

MIT
