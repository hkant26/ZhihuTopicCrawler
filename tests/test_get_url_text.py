import os
import sys
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'codes'))

import requests
from get_url_text import get_url_text


class TestGetUrlText(unittest.TestCase):

    @patch('get_url_text.requests.get')
    def test_successful_request(self, mock_get):
        mock_resp = Mock()
        mock_resp.text = '<html>OK</html>'
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = get_url_text('http://example.com')
        self.assertEqual(result, '<html>OK</html>')
        mock_get.assert_called_once()

    @patch('get_url_text.requests.get')
    def test_http_error(self, mock_get):
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError('404')
        mock_get.return_value = mock_resp

        result = get_url_text('http://example.com')
        self.assertIsNone(result)

    @patch('get_url_text.requests.get')
    def test_connection_error(self, mock_get):
        mock_get.side_effect = requests.ConnectionError('timeout')

        result = get_url_text('http://example.com')
        self.assertIsNone(result)

    @patch('get_url_text.requests.get')
    def test_generic_exception(self, mock_get):
        mock_get.side_effect = RuntimeError('unexpected')

        result = get_url_text('http://example.com')
        self.assertIsNone(result)

    @patch('get_url_text.requests.get')
    def test_headers_contain_required_keys(self, mock_get):
        mock_resp = Mock()
        mock_resp.text = 'ok'
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        get_url_text('http://example.com')
        _, kwargs = mock_get.call_args
        self.assertIn('headers', kwargs)
        self.assertIn('user-agent', kwargs['headers'])
        self.assertIn('cookie', kwargs['headers'])


if __name__ == '__main__':
    unittest.main()
