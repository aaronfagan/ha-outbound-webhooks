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
    AUTH_TYPES_SEND,
    AUTH_X_API_KEY,
    CONF_AUTH_TYPE,
    CONF_CONTENT_TYPE,
    CONF_CREDENTIAL,
    CONF_FOLLOW_REDIRECTS,
    CONF_HEADERS,
    CONF_METHOD,
    CONF_PASSWORD,
    CONF_PAYLOAD,
    CONF_PRESET,
    CONF_TIMEOUT,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_METHOD,
    DEFAULT_TIMEOUT,
    DOMAIN,
    METHODS,
    SERVICE_SEND,
    SERVICE_SEND_PRESET,
    X_API_KEY_HEADER,
)

_LOGGER = logging.getLogger(__name__)

SEND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): cv.string,
        vol.Optional(CONF_METHOD, default=DEFAULT_METHOD): vol.In(METHODS),
        vol.Optional(CONF_HEADERS, default=list): vol.Any(dict, list),
        vol.Optional(CONF_AUTH_TYPE, default=AUTH_NONE): vol.In(AUTH_TYPES_SEND),
        vol.Optional(CONF_CREDENTIAL): cv.string,
        vol.Optional(CONF_PAYLOAD): cv.string,
        vol.Optional(CONF_CONTENT_TYPE, default=DEFAULT_CONTENT_TYPE): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
            vol.Coerce(float), vol.Range(min=1, max=300)
        ),
        vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
        vol.Optional(CONF_FOLLOW_REDIRECTS, default=True): cv.boolean,
    }
)

SEND_PRESET_SCHEMA = vol.Schema({vol.Required(CONF_PRESET): cv.string})


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
    kind = data.get(CONF_AUTH_TYPE, AUTH_NONE)
    credential = data.get(CONF_CREDENTIAL)

    if kind == AUTH_BEARER and credential:
        headers["Authorization"] = f"Bearer {credential}"
    elif kind == AUTH_X_API_KEY and credential:
        headers[X_API_KEY_HEADER] = credential
    elif kind == AUTH_BASIC and data.get(CONF_USERNAME):
        auth = aiohttp.BasicAuth(
            data.get(CONF_USERNAME, ""), data.get(CONF_PASSWORD, "")
        )

    return headers, auth


async def _perform(hass: HomeAssistant, data: dict[str, Any]) -> ServiceResponse:
    url = data.get(CONF_URL)
    if not url:
        raise HomeAssistantError("No URL is configured for this request")

    session = async_get_clientsession(hass, verify_ssl=data.get(CONF_VERIFY_SSL, True))

    headers = _headers(data.get(CONF_HEADERS))
    auth_headers, auth = _auth(data)
    headers.update(auth_headers)

    body = data.get(CONF_PAYLOAD)
    if body:
        headers.setdefault(
            "Content-Type", data.get(CONF_CONTENT_TYPE, DEFAULT_CONTENT_TYPE)
        )

    try:
        async with session.request(
            data.get(CONF_METHOD, DEFAULT_METHOD),
            url,
            headers=headers or None,
            data=body or None,
            auth=auth,
            allow_redirects=data.get(CONF_FOLLOW_REDIRECTS, True),
            timeout=aiohttp.ClientTimeout(total=data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)),
        ) as response:
            text = await response.text()
            return {
                "status": response.status,
                "headers": dict(response.headers),
                "body": text,
            }
    except TimeoutError as err:
        raise HomeAssistantError(f"Request to {url} timed out") from err
    except aiohttp.ClientError as err:
        raise HomeAssistantError(f"Request to {url} failed: {err}") from err


def _register(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, SERVICE_SEND):

        async def handle_send(call: ServiceCall) -> ServiceResponse:
            return await _perform(hass, dict(call.data))

        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND,
            handle_send,
            schema=SEND_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_PRESET):

        async def handle_send_preset(call: ServiceCall) -> ServiceResponse:
            entry = hass.config_entries.async_get_entry(call.data[CONF_PRESET])
            if entry is None or entry.domain != DOMAIN:
                raise HomeAssistantError("The selected preset no longer exists")
            return await _perform(hass, dict(entry.data))

        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_PRESET,
            handle_send_preset,
            schema=SEND_PRESET_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _register(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if len(hass.config_entries.async_entries(DOMAIN)) <= 1:
        for service in (SERVICE_SEND, SERVICE_SEND_PRESET):
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)
    return True
