import json
import unittest
from unittest.mock import patch

import fakeredis

from notify_worker import base
from notify_worker.notify.queue import NotifyQueue

STREAM = 'ejudge.notify'
GROUP = 'rmatics'
CONSUMER = 'rmatics.1'


class TestNotifyQueue(unittest.TestCase):
    """Интеграция с redis streams (на fakeredis)."""

    def setUp(self):
        self._old_client = base.redis._client
        base.redis._client = fakeredis.FakeStrictRedis()
        self.queue = NotifyQueue(STREAM, GROUP, CONSUMER)

    def tearDown(self):
        base.redis._client = self._old_client

    def _push(self, message: dict):
        base.redis.xadd(STREAM, {'data': json.dumps(message)})

    def test_group_created(self):
        groups = base.redis.xinfo_groups(STREAM)
        self.assertEqual(groups[0]['name'], GROUP.encode())

    def test_second_queue_on_same_group_is_ok(self):
        # BUSYGROUP не должен приводить к падению
        NotifyQueue(STREAM, GROUP, 'rmatics.2')

    @patch('notify_worker.notify.queue.process_message')
    def test_message_is_processed_and_acked(self, mock_process):
        message = {'type': 'run', 'run': {'run_uuid': 'u'}}
        self._push(message)

        self.queue.get_and_process()

        mock_process.assert_called_once()
        _, raw = mock_process.call_args[0]
        self.assertEqual(json.loads(raw), message)

        # сообщение подтверждено — pending пуст
        pending = base.redis.xpending(STREAM, GROUP)
        self.assertEqual(pending['pending'], 0)

    @patch('notify_worker.notify.queue.process_message',
           side_effect=RuntimeError('boom'))
    def test_failed_message_is_still_acked(self, mock_process):
        """Текущее поведение: сообщение ack-ается даже при ошибке обработки
        (нотификация теряется — см. отчёт ревью)."""
        self._push({'type': 'run', 'run': {}})

        self.queue.get_and_process()

        pending = base.redis.xpending(STREAM, GROUP)
        self.assertEqual(pending['pending'], 0)
