from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    AUTH_BASIC,
    AUTH_BEARER,
    AUTH_NONE,
    AUTH_TYPES,
    AUTH_X_API_KEY,
    CONF_API_KEY_HEADER,
    CONF_API_KEY_VALUE,
    CONF_AUTH_TYPE,
    CONF_CONTENT_TYPE,
    CONF_FOLLOW_REDIRECTS,
    CONF_HEADERS,
    CONF_METHOD,
    CONF_PASSWORD,
    CONF_PAYLOAD,
    CONF_TIMEOUT,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_API_KEY_HEADER,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_METHOD,
    DEFAULT_TIMEOUT,
    DOMAIN,
    METHODS,
    SERVICE_SEND,
)

_LOGGER = logging.getLogger(__name__)

SEND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): cv.string,
        vol.Optional(CONF_METHOD, default=DEFAULT_METHOD): vol.In(METHODS),
        vol.Optional(CONF_HEADERS, default=list): vol.Any(dict, list),
        vol.Optional(CONF_AUTH_TYPE, default=AUTH_NONE): vol.In(AUTH_TYPES),
        vol.Optional(CONF_TOKEN): cv.string,
        vol.Optional(CONF_API_KEY_HEADER, default=DEFAULT_API_KEY_HEADER): cv.string,
        vol.Optional(CONF_API_KEY_VALUE): cv.string,
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PAYLOAD): cv.string,
        vol.Optional(CONF_CONTENT_TYPE, default=DEFAULT_CONTENT_TYPE): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
            vol.Coerce(float), vol.Range(min=1, max=300)
        ),
        vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
        vol.Optional(CONF_FOLLOW_REDIRECTS, default=True): cv.boolean,
    }
)


def _headers(raw: Any) -> dict[str, str]:
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    result: dict[str, str] = {}
    for row in raw or []:
        if isinstance(row, dict) and row.get("key"):
            result[str(row["key"])] = str(row.get("value", ""))
    return result


def _auth(data: dict[str, Any]) -> tuple[dict[str, str], aiohttp.BasicAuth | None]:
    headers: dict[str, str] = {}
    auth: aiohttp.BasicAuth | None = None
    kind = data[CONF_AUTH_TYPE]

    if kind == AUTH_BEARER and data.get(CONF_TOKEN):
        headers["Authorization"] = f"Bearer {data[CONF_TOKEN]}"
    elif kind == AUTH_X_API_KEY and data.get(CONF_API_KEY_VALUE):
        headers[data[CONF_API_KEY_HEADER]] = data[CONF_API_KEY_VALUE]
    elif kind == AUTH_BASIC and data.get(CONF_USERNAME) is not None:
        auth = aiohttp.BasicAuth(
            data.get(CONF_USERNAME, ""), data.get(CONF_PASSWORD, "")
        )

    return headers, auth


async def _async_send(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    data = call.data
    session = async_get_clientsession(hass, verify_ssl=data[CONF_VERIFY_SSL])

    headers = _headers(data[CONF_HEADERS])
    auth_headers, auth = _auth(data)
    headers.update(auth_headers)

    body = data.get(CONF_PAYLOAD)
    if body is not None:
        headers.setdefault("Content-Type", data[CONF_CONTENT_TYPE])

    try:
        async with session.request(
            data[CONF_METHOD],
            data[CONF_URL],
            headers=headers or None,
            data=body,
            auth=auth,
            allow_redirects=data[CONF_FOLLOW_REDIRECTS],
            timeout=aiohttp.ClientTimeout(total=data[CONF_TIMEOUT]),
        ) as response:
            text = await response.text()
            return {
                "status": response.status,
                "headers": dict(response.headers),
                "body": text,
            }
    except TimeoutError as err:
        raise HomeAssistantError(f"Request to {data[CONF_URL]} timed out") from err
    except aiohttp.ClientError as err:
        raise HomeAssistantError(
            f"Request to {data[CONF_URL]} failed: {err}"
        ) from err


def _register(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SEND):
        return

    async def handle_send(call: ServiceCall) -> ServiceResponse:
        return await _async_send(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND,
        handle_send,
        schema=SEND_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _register(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if len(hass.config_entries.async_entries(DOMAIN)) <= 1:
        hass.services.async_remove(DOMAIN, SERVICE_SEND)
    return True
