from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.outbound_webhooks.const import DOMAIN, SERVICE_SEND


async def _setup(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_send_returns_response(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post("https://example.com/hook", status=200, text='{"ok": true}')

    await _setup(hass)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_SEND,
        {
            "url": "https://example.com/hook",
            "method": "POST",
            "payload": '{"a": 1}',
        },
        blocking=True,
        return_response=True,
    )

    assert response["status"] == 200
    assert response["body"] == '{"ok": true}'
    assert aioclient_mock.call_count == 1


async def test_send_bearer_auth_header(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get("https://example.com/data", status=200, text="ok")

    await _setup(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SEND,
        {
            "url": "https://example.com/data",
            "method": "GET",
            "auth_type": "bearer",
            "token": "secret-token",
        },
        blocking=True,
        return_response=True,
    )

    assert aioclient_mock.call_count == 1
    headers = aioclient_mock.mock_calls[0][3]
    assert headers["Authorization"] == "Bearer secret-token"
