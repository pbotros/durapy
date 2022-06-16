import abc
from typing import Optional, List

from typing_extensions import Type

from durapy.command.model import BaseCommand, PersistedCommand


class CommandDatabase(abc.ABC):
    """
    Contains logic for reading/writing BMI commands to the "database" (Redis in this case). The key is auto-generated
    and contains the Redis timestamp in the form <redis timestamp ms>-<index> (see Redis docs for more detail). There is
    a single field set in this element, with field name 'command' and field value a JSON-encoded version of a BMI
    command.
    """

    @abc.abstractmethod
    def send_command(self, command: BaseCommand) -> PersistedCommand:
        ...

    @abc.abstractmethod
    def fetch_last(self, num: int, offset: int = 0, cursor=None) -> List[PersistedCommand]:
        ...

    @abc.abstractmethod
    def fetch_from(self, num: int, offset: int = 0, cursor=None) -> List[PersistedCommand]:
        ...

    @abc.abstractmethod
    def fetch_next(self, timeout_ms: int) -> Optional[PersistedCommand]:
        ...

    @abc.abstractmethod
    def fetch_by_key(self, key: str) -> Optional[PersistedCommand]:
        ...


class CommandDatabaseFactory(abc.ABC):
    @abc.abstractmethod
    def create(self, command_prefix: str, command_classes: List[Type[BaseCommand]]) -> CommandDatabase:
        ...
