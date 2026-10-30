"""Exercise the real JWT/OAuth SDKs at the application's security boundaries."""
import base64
import hashlib
import json
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
import requests

from backend.services import clinic_google_oauth as oauth


def test_jwt_rejects_non_base64url_signature_suffix():
    key = 'synthetic-regression-key-not-a-real-secret-' * 2
    token = jwt.encode({'sub': 'synthetic-user'}, key, algorithm='HS256')
    assert jwt.decode(token, key, algorithms=['HS256'])['sub'] == 'synthetic-user'
    with pytest.raises(jwt.InvalidTokenError):
        jwt.decode(token + '!!!!', key, algorithms=['HS256'])


def test_real_google_sdk_preserves_pkce_scopes_and_token_exchange(monkeypatch):
    redirect = 'https://clinic.example.test/api/v1/settings/drive/callback'
    config = {'web': {
        'client_id': 'synthetic-client', 'client_secret': 'synthetic-secret',
        'auth_uri': 'https://oauth.example.test/authorize',
        'token_uri': 'https://oauth.example.test/token', 'redirect_uris': [redirect],
    }}
    monkeypatch.setattr(oauth, 'oauth_config', lambda: (config, redirect, 9))
    verifier, state, nonce = 'v' * 64, 'synthetic-state', 'synthetic-nonce'
    url = oauth.authorization_url(state=state, nonce=nonce, verifier=verifier)
    query = parse_qs(urlsplit(url).query)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    assert query['state'] == [state]
    assert query['nonce'] == [nonce]
    assert query['redirect_uri'] == [redirect]
    assert query['code_challenge'] == [challenge]
    assert query['code_challenge_method'] == ['S256']
    assert query['access_type'] == ['offline']
    assert set(query['scope'][0].split()) == set(oauth.SCOPES)

    requests_sent = []

    def send(_session, request, **kwargs):
        requests_sent.append(request)
        assert request.url == config['web']['token_uri']
        assert kwargs['timeout'] == 9
        body = request.body.decode() if isinstance(request.body, bytes) else request.body
        fields = parse_qs(body)
        assert fields['grant_type'] == ['authorization_code']
        assert fields['code_verifier'] == [verifier]
        assert fields['redirect_uri'] == [redirect]
        assert fields['code'] == ['synthetic-code']
        response = requests.Response()
        response.status_code = 200
        response.url = request.url
        response.request = request
        response.headers['Content-Type'] = 'application/json'
        response._content = json.dumps({
            'access_token': 'synthetic-access', 'refresh_token': 'synthetic-refresh',
            'token_type': 'Bearer', 'expires_in': 3600, 'id_token': 'synthetic-id',
            'scope': f'openid {oauth.EMAIL_SCOPE} {oauth.DRIVE_SCOPE}',
        }).encode()
        return response

    def verify(token, _request, *, audience):
        assert token == 'synthetic-id' and audience == config['web']['client_id']
        return {'iss': 'https://accounts.google.com', 'sub': 'synthetic-sub',
                'nonce': nonce, 'email': 'synthetic@example.test'}

    # Keep the SDK and compliance hooks real; replace only remote HTTP and
    # Google's external ID-token verification with synthetic boundaries.
    monkeypatch.setattr(requests.sessions.Session, 'send', send)
    monkeypatch.setattr(oauth.id_token, 'verify_oauth2_token', verify)
    result = oauth.exchange_and_verify(code='synthetic-code', verifier=verifier, nonce_digest=oauth.digest(nonce))
    assert len(requests_sent) == 1
    assert result == {'sub': 'synthetic-sub', 'email': 'synthetic@example.test', 'refresh_token': 'synthetic-refresh'}
