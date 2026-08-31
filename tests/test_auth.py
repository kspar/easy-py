import string
import time
import unittest
from unittest import mock
from urllib.parse import urlparse, parse_qs

import requests

from easy import util
from easy.ez import Ez, TokenType, StorableToken

TEST_PORT = 12345
REDIRECT_URI = f'http://127.0.0.1:{TEST_PORT}/login'


def make_ez(**kwargs):
    return Ez('ems.example.com', 'idp.example.com', 'client.example.com', **kwargs)


def token_endpoint_response():
    return mock.Mock(status_code=200, json=lambda: {'access_token': 'AT', 'expires_in': 300,
                                                    'refresh_token': 'RT', 'refresh_expires_in': 1800})


class PkceTest(unittest.TestCase):
    def test_challenge_matches_rfc7636_appendix_b_vector(self):
        self.assertEqual('E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM',
                         util.pkce_s256_challenge('dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'))

    def test_generated_pair_is_rfc7636_legal(self):
        verifier, challenge = util.generate_pkce_pair()
        self.assertTrue(43 <= len(verifier) <= 128)
        self.assertTrue(set(verifier) <= set(string.ascii_letters + string.digits + '-._~'))
        self.assertEqual(util.pkce_s256_challenge(verifier), challenge)


class EndpointDerivationTest(unittest.TestCase):
    def test_default_realm_path(self):
        ez = make_ez()
        base = 'https://idp.example.com/auth/realms/master/protocol/openid-connect'
        self.assertEqual(base + '/auth', ez.util.idp_auth_url)
        self.assertEqual(base + '/token', ez.util.idp_token_url)
        self.assertEqual(base + '/logout', ez.util.idp_logout_url)

    def test_custom_realm_path_is_normalised(self):
        for given in ('/realms/custom', 'realms/custom', '/realms/custom/'):
            ez = make_ez(idp_realm_path=given)
            self.assertEqual('https://idp.example.com/realms/custom/protocol/openid-connect/token',
                             ez.util.idp_token_url)


class AuthFlowTest(unittest.TestCase):
    def setUp(self):
        self.ez = make_ez()
        self.shutdown = mock.Mock()
        self.app = self.ez.util._create_auth_app(TEST_PORT, self.shutdown)
        self.app.testing = True
        self.client = self.app.test_client()

    def get_callback(self, query: str):
        return self.client.get(f'/login?{query}')

    def start_login(self):
        resp = self.client.get('/login')
        query = parse_qs(urlparse(resp.headers['Location']).query)
        return resp, query

    def assert_no_tokens(self):
        self.assertIsNone(self.ez.util.get_stored_token(TokenType.ACCESS))
        self.assertIsNone(self.ez.util.get_stored_token(TokenType.REFRESH))

    def test_fresh_login_redirects_to_idp_with_pkce(self):
        resp, query = self.start_login()
        self.assertEqual(302, resp.status_code)
        parsed = urlparse(resp.headers['Location'])
        self.assertEqual('https://idp.example.com/auth/realms/master/protocol/openid-connect/auth',
                         f'{parsed.scheme}://{parsed.netloc}{parsed.path}')
        self.assertEqual(['client.example.com'], query['client_id'])
        self.assertEqual([REDIRECT_URI], query['redirect_uri'])
        self.assertEqual(['code'], query['response_type'])
        self.assertEqual(['openid'], query['scope'])
        self.assertEqual(['S256'], query['code_challenge_method'])
        self.assertTrue(query['state'][0])
        self.assertTrue(query['code_challenge'][0])

    def test_health_is_200_and_login_head_is_302(self):
        self.assertEqual(200, self.client.get('/health').status_code)
        self.assertEqual(200, self.client.head('/health').status_code)
        # HEAD on /login is the old readiness probe; it must not be treated as a callback
        self.assertEqual(302, self.client.head('/login').status_code)

    @mock.patch('easy.ez.requests.post')
    def test_full_roundtrip_success(self, post):
        _, query = self.start_login()
        state, challenge = query['state'][0], query['code_challenge'][0]
        post.return_value = token_endpoint_response()

        cb = self.get_callback(f'code=abc&state={state}')

        self.assertEqual(200, cb.status_code)
        body = cb.get_data(as_text=True)
        self.assertIn('Authentication was successful', body)
        self.assertIn('window.close', body)
        self.shutdown.assert_called_once()

        (url,), kwargs = post.call_args
        self.assertEqual(self.ez.util.idp_token_url, url)
        data = kwargs['data']
        self.assertEqual('authorization_code', data['grant_type'])
        self.assertEqual('client.example.com', data['client_id'])
        self.assertEqual('abc', data['code'])
        self.assertEqual(REDIRECT_URI, data['redirect_uri'])
        self.assertEqual(challenge, util.pkce_s256_challenge(data['code_verifier']))

        self.assertEqual('AT', self.ez.util.get_stored_token(TokenType.ACCESS).token)
        self.assertEqual('RT', self.ez.util.get_stored_token(TokenType.REFRESH).token)

    @mock.patch('easy.ez.requests.post')
    def test_user_cancel_renders_fail_page_without_exchange(self, post):
        self.start_login()
        cb = self.get_callback('error=access_denied&error_description=cancelled&state=whatever')
        self.assertIn('Something failed', cb.get_data(as_text=True))
        self.assertNotIn('window.close', cb.get_data(as_text=True))
        post.assert_not_called()
        self.shutdown.assert_called_once()
        self.assert_no_tokens()

    @mock.patch('easy.ez.requests.post')
    def test_forged_state_fails_without_exchange(self, post):
        self.start_login()
        cb = self.get_callback('code=abc&state=forged')
        self.assertIn('Something failed', cb.get_data(as_text=True))
        post.assert_not_called()
        self.shutdown.assert_called_once()
        self.assert_no_tokens()

    @mock.patch('easy.ez.requests.post')
    def test_missing_state_fails_without_exchange(self, post):
        self.start_login()
        cb = self.get_callback('code=abc')
        self.assertIn('Something failed', cb.get_data(as_text=True))
        post.assert_not_called()
        self.assert_no_tokens()

    @mock.patch('easy.ez.requests.post')
    def test_state_is_single_use(self, post):
        _, query = self.start_login()
        state = query['state'][0]
        post.return_value = token_endpoint_response()

        first = self.get_callback(f'code=abc&state={state}')
        self.assertIn('Authentication was successful', first.get_data(as_text=True))

        second = self.get_callback(f'code=abc&state={state}')
        self.assertIn('Something failed', second.get_data(as_text=True))
        post.assert_called_once()
        self.assertEqual(2, self.shutdown.call_count)

    def test_each_login_open_gets_its_own_usable_state(self):
        _, first_query = self.start_login()
        _, second_query = self.start_login()
        self.assertNotEqual(first_query['state'][0], second_query['state'][0])

        with mock.patch('easy.ez.requests.post') as post:
            post.return_value = token_endpoint_response()
            # Completing with the FIRST state must still work after a second tab was opened
            cb = self.get_callback(f"code=abc&state={first_query['state'][0]}")
            self.assertIn('Authentication was successful', cb.get_data(as_text=True))

    @mock.patch('easy.ez.requests.post')
    def test_exchange_error_status_fails(self, post):
        _, query = self.start_login()
        post.return_value = mock.Mock(status_code=400, text='{"error":"invalid_grant"}')
        cb = self.get_callback(f"code=abc&state={query['state'][0]}")
        self.assertIn('Something failed', cb.get_data(as_text=True))
        self.shutdown.assert_called_once()
        self.assert_no_tokens()

    @mock.patch('easy.ez.requests.post')
    def test_exchange_connection_error_fails(self, post):
        _, query = self.start_login()
        post.side_effect = requests.exceptions.ConnectionError('boom')
        cb = self.get_callback(f"code=abc&state={query['state'][0]}")
        self.assertIn('Something failed', cb.get_data(as_text=True))
        self.shutdown.assert_called_once()
        self.assert_no_tokens()

    def test_shutdown_route(self):
        resp = self.client.post('/shutdown')
        self.assertEqual(200, resp.status_code)
        self.shutdown.assert_called_once()


class RefreshTest(unittest.TestCase):
    @mock.patch('easy.ez.requests.post')
    def test_refresh_uses_derived_token_url(self, post):
        ez = make_ez(idp_realm_path='/realms/custom')
        ez.util.set_stored_token(TokenType.REFRESH,
                                 StorableToken(TokenType.REFRESH, 'RT0', round(time.time()) + 3600))
        post.return_value = token_endpoint_response()

        self.assertTrue(ez.util._refresh_using_refresh_token())

        (url,), kwargs = post.call_args
        self.assertEqual('https://idp.example.com/realms/custom/protocol/openid-connect/token', url)
        self.assertEqual('refresh_token', kwargs['data']['grant_type'])
        self.assertEqual('RT0', kwargs['data']['refresh_token'])
        self.assertEqual('AT', ez.util.get_stored_token(TokenType.ACCESS).token)


class LogoutTest(unittest.TestCase):
    @mock.patch('easy.ez.webbrowser.open')
    def test_logout_clears_tokens_and_uses_post_logout_redirect(self, browser_open):
        ez = make_ez()
        ez.util.set_stored_token(TokenType.ACCESS,
                                 StorableToken(TokenType.ACCESS, 'AT', round(time.time()) + 3600))
        ez.logout_in_browser()

        self.assertIsNone(ez.util.get_stored_token(TokenType.ACCESS))
        self.assertIsNone(ez.util.get_stored_token(TokenType.REFRESH))
        url = browser_open.call_args[0][0]
        self.assertTrue(url.startswith('https://idp.example.com/auth/realms/master/protocol/openid-connect/logout?'))
        self.assertIn('client_id=client.example.com', url)
        self.assertIn('post_logout_redirect_uri=https%3A%2F%2Fclient.example.com', url)

    @mock.patch('easy.ez.webbrowser.open')
    def test_custom_logout_redirect_url(self, browser_open):
        ez = make_ez(logout_redirect_url='https://dev.example.com')
        ez.logout_in_browser()
        self.assertIn('post_logout_redirect_uri=https%3A%2F%2Fdev.example.com', browser_open.call_args[0][0])


if __name__ == '__main__':
    unittest.main()
