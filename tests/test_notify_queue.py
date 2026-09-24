import json
import os
import unittest
from unittest.mock import patch, Mock

from notify_worker.config import Config
from notify_worker.notify.queue import (
    _rmatics_run_id,
    _to_int,
    check_client_cert,
    client_cert,
    handle_run_message,
    process_message,
)

RMATICS_URL = 'http://rmatics/problem/run/action/update_from_ejudge'
JUDGE_ID = 1
EJUDGE_API_TOKEN = 'judge-1-token'
FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestToInt(unittest.TestCase):
    def test_int(self):
        self.assertEqual(_to_int('5'), 5)
        self.assertEqual(_to_int(5), 5)

    def test_garbage(self):
        self.assertIsNone(_to_int(None))
        self.assertIsNone(_to_int('abc'))
        self.assertEqual(_to_int('abc', default=0), 0)


class TestRmaticsRunId(unittest.TestCase):
    def test_ext_user_u64(self):
        self.assertEqual(
            _rmatics_run_id({'ext_user_kind': 'u64', 'ext_user': '42'}), 42)

    def test_wrong_kind(self):
        self.assertIsNone(
            _rmatics_run_id({'ext_user_kind': 'str', 'ext_user': '42'}))

    def test_missing_ext_user(self):
        self.assertIsNone(_rmatics_run_id({}))


class TestHandleRunMessage(unittest.TestCase):
    def setUp(self):
        # CONFIG_DICT — живое отображение Config.__dict__
        self._old_url = getattr(Config, 'RMATICS_ALIVE_URL', None)
        self._old_token = getattr(Config, 'EJUDGE_API_TOKEN', None)
        Config.RMATICS_ALIVE_URL = RMATICS_URL
        Config.EJUDGE_API_TOKEN = EJUDGE_API_TOKEN

    def tearDown(self):
        Config.RMATICS_ALIVE_URL = self._old_url
        Config.EJUDGE_API_TOKEN = self._old_token

    def run_data(self, **kwargs):
        data = {
            'run_id': 7,
            'run_uuid': 'uuid-7',
            'contest_id': 3,
            'status': 0,
            'raw_score': 100,
            'raw_test': 5,
            'lang_id': 2,
            'ext_user_kind': 'u64',
            'ext_user': '42',
        }
        data.update(kwargs)
        return data

    @patch('notify_worker.notify.queue.requests.post')
    def test_posts_notification_to_rmatics(self, mock_post):
        mock_post.return_value = Mock(status_code=200)

        handle_run_message(JUDGE_ID, self.run_data())

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], RMATICS_URL)

        sent = kwargs['json']
        self.assertEqual(sent['run_id'], 7)
        self.assertEqual(sent['run_uuid'], 'uuid-7')
        self.assertEqual(sent['contest_id'], 3)
        self.assertEqual(sent['status'], 0)
        self.assertEqual(sent['score'], 100)      # raw_score -> score
        self.assertEqual(sent['test_num'], 5)     # raw_test -> test_num
        self.assertEqual(sent['rmatics_run_id'], 42)
        self.assertEqual(sent['judge_id'], JUDGE_ID)
        self.assertEqual(kwargs['headers']['Authorization'],
                         f'Bearer {EJUDGE_API_TOKEN}')

    @patch('notify_worker.notify.queue.requests.post')
    def test_message_without_uuid_is_skipped(self, mock_post):
        data = self.run_data()
        del data['run_uuid']

        handle_run_message(JUDGE_ID, data)

        mock_post.assert_not_called()

    @patch('notify_worker.notify.queue.requests.post')
    def test_no_ext_user_sends_null_rmatics_run_id(self, mock_post):
        """Посылка не от rmatics (или старый ejudge) — rmatics_run_id=None,
        rmatics найдёт Run по (run_uuid, judge_id)."""
        mock_post.return_value = Mock(status_code=200)
        data = self.run_data()
        del data['ext_user_kind']
        del data['ext_user']

        handle_run_message(JUDGE_ID, data)

        sent = mock_post.call_args[1]['json']
        self.assertIsNone(sent['rmatics_run_id'])


class TestProcessMessage(unittest.TestCase):
    @patch('notify_worker.notify.queue.handle_run_message')
    def test_run_message(self, mock_handle):
        raw = json.dumps({'type': 'run', 'run': {'run_uuid': 'u'}})
        process_message(JUDGE_ID, raw)
        mock_handle.assert_called_once_with(JUDGE_ID, {'run_uuid': 'u'})

    @patch('notify_worker.notify.queue.handle_run_message')
    def test_other_message_type_is_skipped(self, mock_handle):
        process_message(JUDGE_ID, json.dumps({'type': 'ping'}))
        mock_handle.assert_not_called()

    @patch('notify_worker.notify.queue.handle_run_message')
    def test_invalid_json_does_not_crash(self, mock_handle):
        process_message(JUDGE_ID, 'not-a-json{')
        mock_handle.assert_not_called()


class TestClientCert(unittest.TestCase):
    def setUp(self):
        self._old = (Config.RMATICS_CLIENT_CERT, Config.RMATICS_CLIENT_KEY)

    def tearDown(self):
        Config.RMATICS_CLIENT_CERT, Config.RMATICS_CLIENT_KEY = self._old

    def configure(self, cert=None, key=None):
        Config.RMATICS_CLIENT_CERT = cert and os.path.join(FIXTURES, cert)
        Config.RMATICS_CLIENT_KEY = key and os.path.join(FIXTURES, key)

    def test_not_configured(self):
        self.configure()
        self.assertIsNone(client_cert())
        check_client_cert()

    def test_cert_and_key(self):
        self.configure('client.pem', 'client.key')
        self.assertEqual(client_cert(), (Config.RMATICS_CLIENT_CERT,
                                         Config.RMATICS_CLIENT_KEY))
        check_client_cert()

    def test_combined_pem(self):
        self.configure('combined.pem')
        self.assertEqual(client_cert(), Config.RMATICS_CLIENT_CERT)
        check_client_cert()

    def test_key_without_cert(self):
        self.configure(key='client.key')
        with self.assertRaises(RuntimeError):
            check_client_cert()

    def test_missing_file(self):
        self.configure('missing.pem', 'client.key')
        with self.assertRaises(RuntimeError):
            check_client_cert()

    def test_key_does_not_match_cert(self):
        self.configure('client.pem', 'other.key')
        with self.assertRaises(RuntimeError):
            check_client_cert()

    def test_encrypted_key(self):
        self.configure('client.pem', 'encrypted.key')
        with self.assertRaises(RuntimeError):
            check_client_cert()

    @patch('notify_worker.notify.queue.requests.post')
    def test_cert_is_sent(self, mock_post):
        self.configure('client.pem', 'client.key')
        mock_post.return_value = Mock(status_code=200)
        Config.RMATICS_ALIVE_URL, old_url = RMATICS_URL, Config.RMATICS_ALIVE_URL
        try:
            handle_run_message(JUDGE_ID, {'run_uuid': 'u'})
        finally:
            Config.RMATICS_ALIVE_URL = old_url

        self.assertEqual(mock_post.call_args[1]['cert'],
                         (Config.RMATICS_CLIENT_CERT, Config.RMATICS_CLIENT_KEY))
