# CLAUDE.md

**Outbound Webhooks** - a Home Assistant custom integration that adds drag/drop actions to the Automation builder for sending configured HTTP requests (webhooks) to external APIs.

It fills a real gap: HA can only send outbound HTTP via `rest_command`, which is YAML-only and shows in the visual editor as a raw data blob. This integration registers proper actions with `services.yaml` selectors, so the whole request is configured with form fields in the builder - no YAML.

## Current status (resume here)

- **Public** repo `aaronfagan/ha-outbound-webhooks` (dev; not submitted/advertised anywhere yet).
- **v0.2.0 shipped** and running on Aaron's HAOS VM. CI fully green (hassfest + hacs/action + pytest).
- Built: both actions, presets with a config-flow wizard + reconfigure, full auth, brand icon, README.

**Still TODO (the "publishing" work):**
1. **`home-assistant/brands` PR** under `custom_integrations/outbound_webhooks/` - REQUIRED for the icon to actually render on the Devices & Services page. The local `brand/` assets only satisfy HACS *validation*; the displayed icon comes from the brands CDN. Needs an optimized PNG (no optimizer installed locally yet - `brew install oxipng` or similar first).
2. **HACS default-store submission PR** (a PR to the HACS repo). "Tomorrow's problem" per Aaron.
3. **Broader tests** - config-flow tests, auth/error paths (only `send`/`send_preset` happy-path tests exist).
4. Deferred feature: per-call templating for `send_preset` (pass `data` to fill `{{ }}` placeholders). Presets are static today by choice (YAGNI).

## Why an integration, not an add-on

Do not relitigate. An **add-on** is a separate Docker container; it can't register an action into the visual Automation builder. Only an **integration** (Python in HA Core) can register services whose `services.yaml` selectors render as builder form fields. Aaron's `ha-airprint` repo is the reference - we mirror its `custom_components/airprint/` integration half.

## Naming

- Domain `outbound_webhooks`, display name **Outbound Webhooks**.
- **Not "curl":** trademarked; would be rejected by brands/core. We model the feature surface on curl ("works like a curl") but the name is distinct.
- **Not "webhook":** reserved core domain, and it means the *inbound* direction. "Outbound" disambiguates.

## Distribution goals

Build to core-contribution quality, ship via HACS as the minimum: custom-repository (works now) → HACS default store (near-term) → HA Core (stretch; core may resist a generic HTTP sender given `rest_command`). This imposes: config flow, `hassfest` + `hacs/action` CI, `manifest.json` version, `hacs.json`, tagged releases, README + MIT license, brands PR, tests.

## Architecture (as built)

### Two actions

- **`outbound_webhooks.send`** - generic one-off. Flat form (see the HA-UI gotchas - action forms can't be conditional): `url` (text), `method` (dropdown, default GET), `headers` (key/value rows), `auth_type` (None/Basic/Bearer/X-API-Key), `credential` + `username` + `password` (all present, empty when unused), `payload` (template), `content_type`, `timeout`, `verify_ssl`, `follow_redirects`. Every field is `required: true` (that's how the optional-field checkbox is suppressed; empties still submit). Returns `{status, headers, body}` via `response_variable` (`SupportsResponse.OPTIONAL`).
- **`outbound_webhooks.send_preset`** - one field, `preset` (a `config_entry` selector = dropdown of saved presets). Sends that preset's stored config **as-is** (static; no per-call data yet). Same response shape.

### Presets = config-entry-per-preset

Each preset is its own config entry (that's what makes the `config_entry` selector a clean dropdown; subentries have no builder selector). Added via **Settings → Devices & Services → Add Integration → Outbound Webhooks** ("Add another" for more). A preset stores the full request incl. auth + credentials in the entry's `.storage` (out of automation YAML).

- **Config-flow wizard** (`config_flow.py`): `async_step_user` (request) → `async_step_auth` (type) → conditional `async_step_credential` (Bearer/X-API-Key) or `async_step_basic` (username/password), else finish. This multi-step routing is how the *conditional* auth UI is achieved (impossible in the flat action form).
- **Central editing = Reconfigure** (`async_step_reconfigure`): reopens the wizard pre-filled, `async_update_reload_and_abort`. `send_preset` reads `entry.data` **live at call time**, so an edit propagates to every automation using the preset with no automation changes.

### Auth

**None, Basic, Bearer, X-API-Key** (that order - None first, then alphabetical). Bearer → `Authorization: Bearer <credential>`; X-API-Key → `X-API-Key: <credential>` header; Basic → `aiohttp.BasicAuth(username, password)`. The generic `send` shows all fields flat; presets use the conditional wizard. Labels are aligned across both flows.

### Implementation notes

- Both actions funnel through `_perform(hass, data)` in `__init__.py`. `_auth()` returns `(headers, BasicAuth|None)`; `_headers()` normalizes either a list of `{key,value}` rows (from the object selector) or a plain dict.
- Shared aiohttp session (`async_get_clientsession`, honoring `verify_ssl`). **No external `requirements`** in the manifest.
- Services register in `async_setup_entry` (guarded by `has_service`), removed when the last entry unloads. So they exist once ≥1 config entry (preset) exists.
- Templating: HA renders `{{ }}` in `send` action fields before the integration sees them (free). Presets don't template yet.

## HA-UI gotchas (learned the hard way)

- **Action forms (`services.yaml`) can't do conditional field visibility** - no show/hide based on another field. Conditional UX only exists in **config flows** (multi-step), which is why full/Basic auth lives in the preset wizard.
- **Optional fields get an "include" checkbox.** The only way to drop it is `required: true` - and HA still lets you submit a required field empty, so "required" here means "no checkbox, still optional." Every `send` field uses this.
- **Selector rendering:** `template` and `object` selectors render as *code editors*. Use `text` for single-line values; use `object` with `multiple: true` + `fields` (key/value) for header rows.
- **The "Response variable" toggle is core HA**, shown for any response-capable action. Not controllable or removable by the integration.

## Repo layout

```
custom_components/outbound_webhooks/
  __init__.py         # _perform + _auth + _headers; registers send + send_preset in async_setup_entry
  config_flow.py      # multi-step wizard (request -> auth -> credential/basic) + reconfigure
  const.py            # DOMAIN, CONF_*, AUTH_* , METHODS, defaults
  manifest.json       # domain, name, config_flow, integration_type:service, iot_class:cloud_push, version
  services.yaml       # field surface for send + send_preset
  strings.json + translations/en.json   # config-flow steps + service field labels (must stay identical)
  brand/              # icon.svg (source) + icon/icon@2x/logo/logo@2x .png (braces+play mark)
tests/                # pytest-homeassistant-custom-component (asyncio_mode=auto in pytest.ini)
.github/workflows/    # ci.yml (compileall + hassfest + hacs/action + pytest), release.yml (tag==manifest -> gh release)
.github/settings.yml  # repo settings-as-code (private:false, topics via gh)
hacs.json  LICENSE  README.md  scripts/{dev,version}.sh
```

## Conventions

- **HA's conventions win** (sentence-case, its selectors, config-flow patterns).
- **Single version source:** `manifest.json` `"version"`. Never hand-edit for a release; use `scripts/version.sh`.
- **strings.json and translations/en.json must stay identical** (CI-adjacent; the dev workflow diffs them).
- **No bundled secrets.** Credentials flow from the config flow into `.storage`.
- Python: `from __future__ import annotations`, async, type hints, voluptuous + HA selectors.
- **Keep the README current** - any change to actions/fields/behaviour lands in the README in the same commit.
- No inline comments (Aaron's global rule); no em-dashes; commit + push finished work (no AI-attribution trailers).

## Dev loop + gotchas

Test target: Aaron's HAOS VM 100 on the `pve` Proxmox host (see `thefagans-ca` repo `docs/servers/home-assistant-vm.md`). No plain SSH into HAOS - reach it via `ssh pve` → `qm guest exec 100 -- /bin/sh -c '<cmd>'` (base64 nested quotes).

- **`scripts/dev.sh`** pushes the working tree onto the box and restarts Core. This is the fast loop - no version bump, no HACS. Use it constantly.
- **The version label LIES during dev.** `dev.sh` doesn't bump the version, so HACS still shows the last release number even though the code is newer. Trust the deployed files, not the number.
- **Hard-refresh the browser** (Cmd-Shift-R) or use an incognito window after every deploy - the frontend caches `services.yaml` selectors and config-flow forms.
- **Integration + `services.yaml` changes need a Core restart** (dev.sh does it). Config-flow errors surface only at runtime in HA (CI can't catch them) - so test the wizard on the box.

## Releasing (real user path)

```bash
scripts/version.sh <ver>            # sets manifest version, commits, tags v<ver>
git push origin main && git push origin v<ver>
```

`release.yml` fails if tag != manifest, then cuts a GitHub release. HACS only sees releases: in HA, HACS → Outbound Webhooks → Update → restart → hard-refresh. **Patch** for fixes/copy, **minor** for features, **major** for a config-breaking change. Current release: **v0.2.0**.
