from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    ObjectSelector,
    ObjectSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    AUTH_BASIC,
    AUTH_BEARER,
    AUTH_NONE,
    AUTH_X_API_KEY,
    CONF_AUTH_TYPE,
    CONF_CONTENT_TYPE,
    CONF_CREDENTIAL,
    CONF_FOLLOW_REDIRECTS,
    CONF_HEADERS,
    CONF_METHOD,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PAYLOAD,
    CONF_TIMEOUT,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_METHOD,
    DEFAULT_TIMEOUT,
    DOMAIN,
    METHODS,
)

CONTENT_TYPES = [
    "application/json",
    "application/x-www-form-urlencoded",
    "text/plain",
]

AUTH_OPTIONS = [
    SelectOptionDict(value=AUTH_NONE, label="None"),
    SelectOptionDict(value=AUTH_BASIC, label="Basic"),
    SelectOptionDict(value=AUTH_BEARER, label="Bearer"),
    SelectOptionDict(value=AUTH_X_API_KEY, label="X-API-Key"),
]

_HEADER_FIELDS = {
    "key": {"selector": {"text": {}}},
    "value": {"selector": {"text": {}}},
}


def _request_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): TextSelector(),
            vol.Required(CONF_URL, default=defaults.get(CONF_URL, "")): TextSelector(),
            vol.Required(
                CONF_METHOD, default=defaults.get(CONF_METHOD, DEFAULT_METHOD)
            ): SelectSelector(
                SelectSelectorConfig(options=METHODS, mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(
                CONF_HEADERS, default=defaults.get(CONF_HEADERS, [])
            ): ObjectSelector(
                ObjectSelectorConfig(
                    multiple=True, label_field="key", fields=_HEADER_FIELDS
                )
            ),
            vol.Optional(
                CONF_PAYLOAD, default=defaults.get(CONF_PAYLOAD, "")
            ): TemplateSelector(),
            vol.Required(
                CONF_CONTENT_TYPE,
                default=defaults.get(CONF_CONTENT_TYPE, DEFAULT_CONTENT_TYPE),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=CONTENT_TYPES,
                    mode=SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                )
            ),
            vol.Required(
                CONF_TIMEOUT, default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1, max=300, mode=NumberSelectorMode.BOX, unit_of_measurement="s"
                )
            ),
            vol.Required(
                CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, True)
            ): BooleanSelector(),
            vol.Required(
                CONF_FOLLOW_REDIRECTS,
                default=defaults.get(CONF_FOLLOW_REDIRECTS, True),
            ): BooleanSelector(),
        }
    )


class OutboundWebhooksConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_auth()

        return self.async_show_form(
            step_id="user", data_schema=_request_schema(self._data)
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if not self._data:
            self._data = dict(self._get_reconfigure_entry().data)
        return await self.async_step_user(user_input)

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            kind = user_input[CONF_AUTH_TYPE]
            self._data[CONF_AUTH_TYPE] = kind
            if kind in (AUTH_BEARER, AUTH_X_API_KEY):
                return await self.async_step_credential()
            if kind == AUTH_BASIC:
                return await self.async_step_basic()
            return self._finish()

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AUTH_TYPE,
                        default=self._data.get(CONF_AUTH_TYPE, AUTH_NONE),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=AUTH_OPTIONS, mode=SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
        )

    async def async_step_credential(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._data[CONF_CREDENTIAL] = user_input.get(CONF_CREDENTIAL, "")
            self._data.pop(CONF_USERNAME, None)
            self._data.pop(CONF_PASSWORD, None)
            return self._finish()

        return self.async_show_form(
            step_id="credential",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CREDENTIAL, default=self._data.get(CONF_CREDENTIAL, "")
                    ): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
        )

    async def async_step_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._data[CONF_USERNAME] = user_input.get(CONF_USERNAME, "")
            self._data[CONF_PASSWORD] = user_input.get(CONF_PASSWORD, "")
            self._data.pop(CONF_CREDENTIAL, None)
            return self._finish()

        return self.async_show_form(
            step_id="basic",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_USERNAME, default=self._data.get(CONF_USERNAME, "")
                    ): TextSelector(),
                    vol.Optional(
                        CONF_PASSWORD, default=self._data.get(CONF_PASSWORD, "")
                    ): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
        )

    def _finish(self) -> ConfigFlowResult:
        title = self._data.get(CONF_NAME) or self._data.get(CONF_URL) or "Webhook"

        if self.source == SOURCE_RECONFIGURE:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(), title=title, data=self._data
            )

        return self.async_create_entry(title=title, data=self._data)
