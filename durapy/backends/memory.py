import time
import uuid
from typing import Optional, List

from more_itertools import only
from typing_extensions import Type

from durapy.backends.base import CommandDatabase, CommandDatabaseFactory
from durapy.command.model import BaseCommand, PersistedCommand


class InMemoryCommandDatabase(CommandDatabase):
    """
    In-memory command database, FOR USE IN TESTING. This purely stores commands in this process's memory and so is not
    suitable for use in real setups to communicate across different processes.
    """

    def __init__(self):
        self._commands = []
        self._commands_cur_idx = 0

    def send_command(self, command: BaseCommand) -> PersistedCommand:
        p = PersistedCommand(
            command=command,
            key=str(uuid.uuid4()),
            timestamp_ms=int(1e3 * time.time()),
        )
        self._commands.append(p)
        return p

    def fetch_last(self, num: int, offset: int = 0, cursor=None) -> List[PersistedCommand]:
        # Being lazy
        assert cursor is None
        return self._commands[offset:offset + num][::-1]

    def fetch_from(self, num: int, offset: int = 0, cursor=None) -> List[PersistedCommand]:
        # Being lazy
        assert cursor is None
        return self._commands[offset:offset + num]

    def fetch_next(self, timeout_ms: int) -> Optional[PersistedCommand]:
        if self._commands_cur_idx >= len(self._commands):
            time.sleep(timeout_ms/1000)
            return None
        ret = self._commands[self._commands_cur_idx]
        self._commands_cur_idx += 1
        return ret

    def fetch_by_key(self, key: str) -> Optional[PersistedCommand]:
        return only([c for c in self._commands if c.key == key])


class InMemoryCommandDatabaseFactory(CommandDatabaseFactory):
    def create(self, command_prefix: str, command_classes: List[Type[BaseCommand]]) -> CommandDatabase:
        return InMemoryCommandDatabase()
