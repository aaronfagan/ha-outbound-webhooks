# Outbound Webhooks

A Home Assistant integration that lets your automations send configured HTTP requests (webhooks) to external APIs - as drag/drop actions in the automation builder. No YAML, no shell, no `rest_command`.

It works like a `curl`: pick a method, set headers and auth, add a body, and optionally capture the response.

Two ways to use it:

- **Send request** - a one-off request you configure right in the automation step.
- **Send preset** - a request you save once and reuse across many automations, edited in one place.

## Install

**HACS (custom repository)**

1. HACS → three-dot menu → **Custom repositories**.
2. Add `https://github.com/aaronfagan/ha-outbound-webhooks`, category **Integration**.
3. Install **Outbound Webhooks**, then restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → Outbound Webhooks** to create your first preset (optional - the **Send request** action works without one).

## Send request (one-off)

Add an action, choose **Outbound Webhooks: Send request**, and fill in the fields:

```yaml
actions:
  - action: outbound_webhooks.send
    data:
      url: "https://api.example.com/v1/events"
      method: POST
      auth_type: bearer
      credential: !secret my_api_token
      content_type: application/json
      payload: '{"event": "{{ trigger.id }}", "at": "{{ now().isoformat() }}"}'
    response_variable: result
  - if: "{{ result.status != 200 }}"
    then:
      - action: persistent_notification.create
        data:
          message: "Webhook failed: {{ result.status }}"
```

### Fields

| Field | What it does |
|---|---|
| **URL** | Where to send the request (templates allowed) |
| **Method** | GET / POST / PUT / PATCH / DELETE |
| **Headers** | Extra request headers, as key/value rows |
| **Authentication** | None, Basic, Bearer, or X-API-Key |
| **API key / token** | The Bearer token or X-API-Key value |
| **Username** / **Password** | For Basic authentication |
| **Payload** | The request body (templates allowed) |
| **Content type** | Content-Type for the body |
| **Timeout** | Seconds before giving up (default 10) |
| **Verify SSL** | Verify the server's TLS certificate (default on) |
| **Follow redirects** | Follow HTTP redirects (default on) |

Only fill the auth fields you need - the rest can stay empty.

## Send preset (reusable)

A **preset** is a complete request - URL, method, headers, auth, payload, everything - saved once and fired from as many automations as you like. Edit the preset in one place and every automation using it follows.

**Create one:** Settings → Devices & Services → **Add Integration → Outbound Webhooks**. A short wizard collects the request, then the authentication (Basic asks for username/password; Bearer and X-API-Key ask for a single key; None skips it). Add more with **Add another**.

**Use it in an automation:**

```yaml
actions:
  - action: outbound_webhooks.send_preset
    data:
      preset: "Notify Billing API"   # a dropdown of your saved presets
    response_variable: result
```

**Edit it centrally:** Settings → Devices & Services → Outbound Webhooks → your preset → **Reconfigure**. The change applies to every automation that uses the preset - you don't touch the automations.

## Authentication

Both actions support **None**, **Basic** (username + password), **Bearer** (`Authorization: Bearer <token>`), and **X-API-Key** (`X-API-Key: <value>`). Preset credentials are stored in Home Assistant's config storage, not in your automation YAML.

## Response

Set `response_variable` on either action to capture:

- `status` - the HTTP status code
- `headers` - the response headers
- `body` - the response body as text

Leave it off for fire-and-forget.

## License

MIT
