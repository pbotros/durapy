import json
import logging
from typing import Optional, Dict, Any, List, Union, Tuple, Type

import redis  # type: ignore
from more_itertools import only  # type: ignore

from durapy.backends.base import CommandDatabase, CommandDatabaseFactory
from durapy.command.model import BaseCommand, PersistedCommand


class RedisCommandDatabaseFactory(CommandDatabaseFactory):
    def __init__(self, redis_hostname: str, redis_port: int, redis_password: Optional[str] = None):
        self._redis_hostname = redis_hostname
        self._redis_port = redis_port
        self._redis_password = redis_password

    def create(self, command_prefix: str, command_classes: List[Type[BaseCommand]]):
        return _RedisCommandDatabase(
            command_prefix=command_prefix,
            command_classes=command_classes,
            redis_hostname=self._redis_hostname,
            redis_port=self._redis_port,
            redis_password=self._redis_password,
        )


class _RedisCommandDatabase(CommandDatabase):
    """
    Contains logic for reading/writing commands to the Redis database.

    The key is auto-generated and contains the Redis timestamp in the form <redis timestamp ms>-<index> (see Redis docs
    for more detail). There is a single field set in this element, with field name 'command' and field value a
    JSON-encoded version of a BMI command.
    """
    def __init__(
            self,
            command_prefix: str,
            command_classes: List[Type[BaseCommand]],
            redis_hostname: str,
            redis_port: int,
            redis_password: Optional[str] = None):
        self._command_stream_name = f'{command_prefix}_commands'
        self._redis = redis.StrictRedis(host=redis_hostname,
                                        port=redis_port,
                                        password=redis_password)
        self._command_classes = command_classes

        # Initialize our internal cursor to the last entry in the stream
        last_command = self._redis.xrevrange(self._command_stream_name, count=1)
        if len(last_command) == 0:
            # Guaranteed to always be before all commands
            self.last_seen = '0-0'
        else:
            self.last_seen = last_command[0][0]

    def send_command(self, command: BaseCommand) -> PersistedCommand:
        command_dict = self._command_to_dict(command)
        logging.info("Sending command {}".format(command_dict))

        key = self._redis.xadd(self._command_stream_name, fields={
            'command': json.dumps(command_dict)
        })
        key = key.decode('ascii')
        ret = self.fetch_by_key(key)
        if ret is None:
            raise ValueError(f'Could not find command even though it was just persisted? key={key}, command={command}')
        return ret

    def fetch_last(self, num: int, offset: int = 0, cursor=None) -> List[PersistedCommand]:
        max_key = _decrement_key(cursor) if cursor is not None else self.last_seen
        results = self._redis.xrevrange(self._command_stream_name, max=max_key, count=num + offset)

        return [self._from_redis(key, entry) for key, entry in results[offset:]]

    def fetch_from(self, num: int, offset: int = 0, cursor=None) -> List[PersistedCommand]:
        min_key = _increment_key(cursor) if cursor is not None else '-'
        results = self._redis.xrange(self._command_stream_name, min=min_key, count=num)

        return [self._from_redis(key, entry) for key, entry in results[offset:]]

    def fetch_next(self, timeout_ms: int) -> Optional[PersistedCommand]:
        results = self._redis.xread(
            {self._command_stream_name: self.last_seen}, count=1,
            block=int(round(timeout_ms)))
        if len(results) == 0:
            return None

        result = only(results)
        if len(result) != 2:
            raise ValueError("Unexpected format; expected [stream_name, [list of results]], got {}".format(result))

        key, entry = only(result[1])
        self.last_seen = key
        return self._from_redis(key, entry)

    def fetch_by_key(self, key: str) -> Optional[PersistedCommand]:
        results = self._redis.xrevrange(self._command_stream_name, min=key, max=key, count=1)

        if len(results) == 0:
            return None
        fetched_key, entry = only(results)
        return self._from_redis(fetched_key, entry)

    def _from_redis(self, redis_key: bytes, redis_entry):
        d = json.loads(redis_entry[b'command'])
        timestamp_ms = _decode_key(redis_key)[0]
        key = redis_key.decode('ascii') if isinstance(redis_key, bytes) else redis_key
        return self._dict_to_command(d, key, timestamp_ms)

    def _dict_to_command(self, command_dict: Dict[str, Any], redis_key: str, redis_timestamp_ms: int) -> \
            PersistedCommand:
        command_type = command_dict['type']
        command_class: Optional[Type[BaseCommand]] = \
            only([clazz for clazz in self._command_classes if clazz.type() == command_type])
        if command_class is None:
            raise ValueError(f'Command type {command_type} is not registered.')

        command = command_class.from_dict(command_dict['command'])
        return PersistedCommand(command=command, key=redis_key, timestamp_ms=redis_timestamp_ms)

    def _command_to_dict(self, command: BaseCommand) -> Dict[str, Any]:
        command_dict = command.to_dict()
        command_class: Optional[Type[BaseCommand]] = \
            only([clazz for clazz in self._command_classes if clazz.type() == command.type()])
        if command_class is None:
            raise ValueError(f'Attempting to send a command of type {command.type()} without a registered type?')
        return {
            'type': command.type(),
            'command': command_dict,
        }


def _decode_key(key: Union[str, bytes]) -> Tuple[int, int]:
    if isinstance(key, bytes):
        key = key.decode('ascii')
    if key == '-':
        return (0, 0)
    last_key_split = key.split('-')
    return int(last_key_split[0]), int(last_key_split[1])


def _encode_key(key1: int, key2: int) -> str:
    return '{}-{}'.format(key1, key2)


def _increment_key(key: Union[str, bytes]) -> str:
    decoded_key = _decode_key(key)
    if decoded_key[1] == 18446744073709551615:
        return _encode_key(decoded_key[0] + 1, 0)
    else:
        return _encode_key(decoded_key[0], decoded_key[1] + 1)


def _decrement_key(key: Union[str, bytes]) -> str:
    decoded_key = _decode_key(key)
    if decoded_key[1] == 0:
        return _encode_key(decoded_key[0] - 1, 18446744073709551615)
    else:
        return _encode_key(decoded_key[0], decoded_key[1] - 1)
