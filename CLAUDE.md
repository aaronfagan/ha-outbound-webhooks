# CLAUDE.md

**Outbound Webhooks** - a Home Assistant custom integration that adds drag/drop actions to the Automation builder for sending configured HTTP requests (webhooks) to external APIs.

It fills a real gap: Home Assistant can only send outbound HTTP via `rest_command`, which is YAML-only and appears in the visual editor as a raw data blob. This integration registers proper actions with `services.yaml` selectors, so the whole request (URL, method, headers, auth, body) is configured with form fields in the builder - no YAML.

Status: greenfield. Repo `aaronfagan/ha-outbound-webhooks`, **private until tested** on the HAOS VM.

## Why an integration, not an add-on

Do not relitigate this. An **add-on** is a separate Docker container; it can talk to HA over MQTT or the API but **cannot register an action into the visual Automation builder**. Only an **integration** (Python running inside HA Core) can register services/actions whose `services.yaml` selectors render as form fields in the editor. That builder step is the entire point, so this is an integration. (Aaron's `ha-airprint` repo is the reference - it has both halves; we mirror only its `custom_components/airprint/` integration half.)

## Naming

- Domain `outbound_webhooks`, display name **Outbound Webhooks**.
- **Not "curl":** curl is a trademarked project; naming it that implies affiliation and would be rejected by the `home-assistant/brands` repo and core review. We model the *feature surface* on curl and use "works like a curl" as the docs framing, but the name is distinct.
- **Not "webhook":** `webhook` is a reserved core domain and means the *inbound* direction (automations trigger on an incoming webhook to HA). "Outbound" disambiguates and avoids the collision.

## Distribution goals

Build to **core-contribution quality**, ship via **HACS as the minimum**:

- **HACS custom repository** - installable by pasting the GitHub URL. Works day one.
- **HACS default store** - a PR to the HACS repo; needs passing structure/manifest/brands/releases validation. The near-term target.
- **Home Assistant Core** - stretch goal. Highest bar (quality scale, tests, config flow, brands PR, review). Honest caveat: core may resist a generic HTTP sender given `rest_command` exists, so core is aspirational, not the launch plan.

Requirements this imposes (build them in from the start): a config flow, `hassfest` + `hacs/action` CI, `manifest.json` with `version`, `hacs.json`, tagged releases, README + OSI license, a `home-assistant/brands` PR (icon/logo), and tests.

## Architecture

### Two actions

- **`outbound_webhooks.send`** - generic one-off request. Selectors: `url` (template), `method` (GET/POST/PUT/PATCH/DELETE), `headers` (key/value, template), `auth` (`none`/`bearer`/`x_api_key`/`basic` + conditional credential fields), `payload` (template) + `content_type` (application/json, x-www-form-urlencoded, text/plain, custom), `timeout` (default 10s), `verify_ssl` (default on), `follow_redirects`. Returns `{status, headers, body}` via `response_variable` (`SupportsResponse.OPTIONAL` - capture or fire-and-forget).
- **`outbound_webhooks.send_preset`** - pick a saved preset via a `ConfigEntrySelector` dropdown, plus a `data` object whose values fill `{{ }}` placeholders in the preset's stored URL/headers/body, plus optional inline overrides.

### Presets = config-entry-per-preset

Each preset is its own config entry, added via **Settings → Devices & Services → Add Integration → Outbound Webhooks** ("add another" for more). This is deliberate: entry-per-preset is what makes the `ConfigEntrySelector` dropdown work in the builder. (Subentries, as `ha-airprint` uses for printers, have no builder selector, so they lose the drag/drop pick.)

A preset stores: name, url, method, headers, auth type + **credentials** (Bearer token / API key / Basic user+pass), body template, content_type, defaults. **Secrets live in the config entry** (HA `.storage`) - the established UI way, keeping tokens out of YAML.

### Auth set

Exactly four: **None, Bearer, X-API-Key, Basic.** Nothing else in MVP.

### Implementation notes

- Use HA's shared aiohttp session (`homeassistant.helpers.aiohttp_client.async_get_clientsession`). **No external `requirements`** in the manifest - keeps it light and core-friendly.
- Templating is free for the generic action: HA renders `{{ }}` in action fields before the integration sees them. For presets, render the stored template against the passed `data` with HA's template engine at call time.
- Register the generic `send` action on component load (`async_setup`) so it exists even with zero presets.

### curl-inspired feature roadmap

MVP is the surface above. Later (curl analogs): query-param builder (`--data-urlencode`), multipart/file upload (`-F`), mTLS client certs (`--cert`), cookies (`-b`), retries (`--retry`).

## Repo layout

```
custom_components/outbound_webhooks/
  __init__.py         # async_setup: register send + send_preset; per-entry preset setup
  config_flow.py      # add/edit presets via UI
  const.py            # DOMAIN, method/auth/content-type constants, defaults
  manifest.json       # domain, name, config_flow:true, version, codeowners, iot_class
  services.yaml       # the drag/drop field surface for both actions
  strings.json
  translations/en.json
  brand/              # icon.png + logo.png (for the brands PR)
tests/                # pytest-homeassistant-custom-component: config-flow + action tests
.github/
  settings.yml        # repo settings-as-code (adapted from ha-airprint)
  FUNDING.yml
  workflows/ci.yml    # compileall + hassfest + hacs/action (no Docker)
  workflows/release.yml  # tag==manifest version check + gh release (no GHCR)
hacs.json             # {name:"Outbound Webhooks", content_in_root:false, render_readme:true}
scripts/dev.sh        # push integration to HAOS VM + restart HA Core
scripts/version.sh    # bump manifest version, commit, tag
LICENSE  README.md  CLAUDE.md  .gitignore
```

Borrowed from `ha-airprint` (integration half): config-flow patterns, CI gates (`hassfest` + `hacs/action`), the release version-gate, `scripts/version.sh` + `scripts/dev.sh`, `hacs.json`, `.github/settings.yml`. Dropped (add-on-only): the `airprint/` dir, Docker CI, `repository.yaml`, the "versions agree" job (single version source now), shellcheck.

## Conventions

- **Home Assistant's conventions win.** Sentence-case names, its selectors, its config-flow patterns. If a request conflicts, say so before deviating.
- **Single version source:** `custom_components/outbound_webhooks/manifest.json` `"version"`. Never hand-edit for a release; use `scripts/version.sh`.
- **The data model mirrors the UI** - one stored key per field the user sees.
- **No bundled secrets.** Credentials come from the config flow into `.storage`, never committed.
- Python: `from __future__ import annotations`, async throughout, type hints, `voluptuous` schemas with HA selectors.
- **Keep the README current** - any change to actions, fields, or behaviour lands in the README in the same commit. Write for a HA user who wants to fire a webhook from an automation, not for the author.

## Testing on the HAOS VM

The test target is Aaron's Home Assistant OS VM (VM 100 on the `pve` Proxmox host; documented in the `thefagans-ca` repo at `docs/servers/home-assistant-vm.md`). There is no plain SSH into HAOS - reach root + docker through the guest agent:

```bash
ssh pve
qm guest exec 100 -- /bin/sh -c '<command>'
# base64-encode anything with nested quotes
```

- **Integration changes only take effect on an HA Core restart** - copying files in is not enough (`ha core restart`).
- `scripts/dev.sh` pushes `custom_components/outbound_webhooks/` onto the box and restarts Core.
- Verify against the real thing (add the integration, build a test automation, fire it, capture the response) rather than asserting it works.

## Releasing

```bash
scripts/version.sh 0.1.0     # sets manifest version, commits, tags v0.1.0
git push origin main && git push origin v0.1.0
```

Pushing the tag runs `release.yml`, which fails if the tag and `manifest.json` disagree, then cuts a GitHub release. **Patch** for fixes/copy, **minor** for features, **major** for a config-breaking change.

## Getting a change onto Home Assistant

Two tracks - pick by what you're testing:

- **Fast local iteration** (`scripts/dev.sh`): pushes the working tree straight onto VM 100 and restarts Core. No version bump, no release, no HACS. Use this for rapid edit/test loops.
- **Release + HACS update** (the real user path): HACS only sees **releases**, so a change reaches an installed instance only after a new tag:
  1. `scripts/version.sh <ver>` then push `main` + the tag - `release.yml` cuts the release.
  2. In HA: **HACS** - open Outbound Webhooks - **Update** / **Redownload** the new version (HACS shows it once its background check sees the tag; restart HA or wait if it lags).
  3. **Restart Home Assistant** (integrations need a Core restart), then **hard-refresh the browser** - the frontend caches `services.yaml` selectors.

Either way, a Core restart is required for Python or `services.yaml` changes to take effect.

## Next step

Design is agreed; the formal spec + implementation plan are the next artifacts (to live under `docs/`). Until then this file is the source of truth for intent.
