"""Small, centralized HTTP client for outbound n8n workflow calls."""

import json
from urllib import error, request

from django.conf import settings


class N8NClientError(RuntimeError):
    """Base class for failures while communicating with n8n."""


class N8NConfigurationError(N8NClientError):
    pass


class N8NConnectionError(N8NClientError):
    pass


class N8NHTTPError(N8NClientError):
    def __init__(self, status_code):
        self.status_code = status_code
        super().__init__(f'n8n returned HTTP {status_code}')


class N8NResponseError(N8NClientError):
    pass


class N8NClient:
    def __init__(self, timeout=None, service_secret=None):
        self.timeout = timeout if timeout is not None else settings.N8N_REQUEST_TIMEOUT
        self.service_secret = service_secret if service_secret is not None else settings.N8N_SERVICE_SECRET

    def post_json(self, url, payload, *, idempotency_key=None):
        if not url:
            raise N8NConfigurationError('n8n workflow URL is not configured')
        if not self.service_secret and not settings.DEBUG:
            raise N8NConfigurationError('n8n service authentication is not configured')

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        if self.service_secret:
            headers['X-N8N-Service-Secret'] = self.service_secret
        if idempotency_key:
            headers['Idempotency-Key'] = str(idempotency_key)

        api_request = request.Request(
            url=url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        try:
            with request.urlopen(api_request, timeout=self.timeout) as response:
                raw_body = response.read().decode('utf-8')
        except error.HTTPError as exception:
            raise N8NHTTPError(exception.code) from exception
        except (error.URLError, TimeoutError, OSError) as exception:
            raise N8NConnectionError('Could not connect to n8n') from exception

        if not raw_body.strip():
            raise N8NResponseError('n8n returned an empty response')
        try:
            response_payload = json.loads(raw_body)
        except json.JSONDecodeError as exception:
            raise N8NResponseError('n8n returned invalid JSON') from exception
        if not isinstance(response_payload, dict):
            raise N8NResponseError('n8n response must be a JSON object')
        return response_payload


def start_mission_generation(payload, *, idempotency_key=None):
    """Start the configured mission workflow using the versioned contract payload."""
    return N8NClient().post_json(
        settings.N8N_MISSION_GENERATION_URL,
        payload,
        idempotency_key=idempotency_key,
    )


def start_research_collection(payload, *, idempotency_key=None):
    """Start the asynchronous AI Finance Research collector."""
    return N8NClient().post_json(
        settings.N8N_RESEARCH_COLLECTOR_URL,
        payload,
        idempotency_key=idempotency_key,
    )
