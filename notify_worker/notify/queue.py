import json
import logging
import requests
import datetime
import pickle
import mysql.connector

from notify_worker.config import CONFIG_DICT
from notify_worker.utils.queue import RedisStreamsQueue

from typing import Optional

REQUEST_TIMEOUT = 10  # seconds

NON_TERMINAL_STATUSES = {
    98,  # 98
    96,    # 96
    377,   # 377
}

def _to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def _is_terminal(status: Optional[int]) -> bool:
    return status is not None and status not in NON_TERMINAL_STATUSES

def _rmatics_run_id(run_data: dict) -> Optional[int]:
    if run_data.get('ext_user_kind') != 'u64':
        return None
    return _to_int(run_data.get('ext_user'))

def handle_run_message(judge_id: int, run_data: dict):
    ej_run_uuid = run_data.get('run_uuid')

    if ej_run_uuid is None:
        logging.error(
            f'notify: message without run_uuid: {run_data!r}'
        )
        return

    connection = mysql.connector.connect(**CONFIG_DICT["MYSQL_CONFIG"])
    cursor = connection.cursor(dictionary=True)

    query = "SELECT run_id, run_uuid, contest_id, score, status, lang_id, test_num, create_time, last_change_time FROM ejudge.runs WHERE run_uuid = %s;"
    cursor.execute(query, (ej_run_uuid,))
    result = cursor.fetchone()
    cursor.close()

    # Надо отдельно обработать даты
    result['create_time'] = result['create_time'].isoformat()
    result['last_change_time'] = result['last_change_time'].isoformat()

    result['rmatics_run_id'] = _rmatics_run_id(run_data)
    result['judge_id'] = judge_id

    r = requests.post(
        CONFIG_DICT['RMATICS_ALIVE_URL'], json=result, timeout=REQUEST_TIMEOUT
    )
    r.raise_for_status()


def process_message(judge_id: int, raw: str):
    """Разобрать одно сообщение из stream и применить его."""
    try:
        message = json.loads(raw)
    except (TypeError, ValueError):
        logging.warning(f'notify: cannot decode message {raw!r}')
        return

    msg_type = message.get('type')

    if msg_type == 'run':
        handle_run_message(judge_id, message.get('run') or {})
    else:
        logging.debug(f'notify: skip message type {msg_type!r}')

class NotifyQueue(RedisStreamsQueue):
    
    def __init__(self, stream, group, consumer):
        super(NotifyQueue, self).__init__(stream=stream, group=group, consumer=consumer)

    def get_and_process(self):
        resp = super(NotifyQueue, self).get_blocking()
        logging.info('ejudge notification')
        if not resp:
            return
        for _, messages in resp:
            for message_id, fields in messages:
                data = fields.get(b'data') or fields.get('data')

                if isinstance(data, bytes):
                    data = data.decode('utf-8', 'replace')

                try:
                    if data is not None:
                        jid = CONFIG_DICT['JUDGE_ID']
                        process_message(jid, data)
                except Exception:
                    logging.exception(
                        'notify-worker: failed to process message'
                    )
                finally:
                    super(NotifyQueue, self).ack(message_id)
