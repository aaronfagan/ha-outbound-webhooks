DOMAIN = "outbound_webhooks"

SERVICE_SEND = "send"

CONF_URL = "url"
CONF_METHOD = "method"
CONF_HEADERS = "headers"
CONF_AUTH_TYPE = "auth_type"
CONF_CREDENTIAL = "credential"
CONF_PAYLOAD = "payload"
CONF_CONTENT_TYPE = "content_type"
CONF_TIMEOUT = "timeout"
CONF_VERIFY_SSL = "verify_ssl"
CONF_FOLLOW_REDIRECTS = "follow_redirects"

AUTH_NONE = "none"
AUTH_BEARER = "bearer"
AUTH_X_API_KEY = "x_api_key"
AUTH_TYPES = [AUTH_NONE, AUTH_BEARER, AUTH_X_API_KEY]

X_API_KEY_HEADER = "X-API-Key"

METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

DEFAULT_METHOD = "GET"
DEFAULT_CONTENT_TYPE = "application/json"
DEFAULT_TIMEOUT = 10
