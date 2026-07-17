DOMAIN = "outbound_webhooks"

SERVICE_SEND = "send"

CONF_URL = "url"
CONF_METHOD = "method"
CONF_HEADERS = "headers"
CONF_AUTH_TYPE = "auth_type"
CONF_TOKEN = "token"
CONF_API_KEY_HEADER = "api_key_header"
CONF_API_KEY_VALUE = "api_key_value"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PAYLOAD = "payload"
CONF_CONTENT_TYPE = "content_type"
CONF_TIMEOUT = "timeout"
CONF_VERIFY_SSL = "verify_ssl"
CONF_FOLLOW_REDIRECTS = "follow_redirects"

AUTH_NONE = "none"
AUTH_BEARER = "bearer"
AUTH_X_API_KEY = "x_api_key"
AUTH_BASIC = "basic"
AUTH_TYPES = [AUTH_NONE, AUTH_BEARER, AUTH_X_API_KEY, AUTH_BASIC]

METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

DEFAULT_METHOD = "POST"
DEFAULT_CONTENT_TYPE = "application/json"
DEFAULT_API_KEY_HEADER = "X-API-Key"
DEFAULT_TIMEOUT = 10
