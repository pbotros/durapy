import abc
import dataclasses
from enum import Enum
from typing import TypeVar, List, Callable, Optional

from dataclasses_json import DataClassJsonMixin


class BaseCommand(DataClassJsonMixin):
    """
    Base class to extend for all commands. Your command class should be a Python dataclass, containing data fields
    that are immutable and are able to be serialized to JSON. Extend this class per command you want to handle. The
    "type" (as returned by the #type() method below) should be the unique identifier for any given command, and should
    never change (or else historical instances of that command may fail to parse).
    """
    @staticmethod
    @abc.abstractmethod
    def type() -> str:
        ...


def oneof_class(clazz_name: str, values: List[str]):
    """
    Shortcut for creating an Enum representing a configuration parameter. Both the key and value are set as the target
    string in the enum to make serialization/deserialization unambiguous. Use this method if you want to represent
    an enum within a command class.

    Example usage:

    @dataclass
    class YourCommand(BaseCommand):
        ...
        some_enum: oneof_class('some_enum', [
            'val1',
            'val2',
            'val3',
            ...
        ])
    """
    return Enum(clazz_name, [(v, v) for v in values])


CommandT = TypeVar('CommandT', bound='Command')


@dataclasses.dataclass
class PersistedCommand(DataClassJsonMixin):
    """
    A command that has been sent. Sending a command adds a unique key to the command and a (server-based) timestamp of
    when the command was sent.
    """
    command: BaseCommand

    # Unique key identifying this command. The format of the key is dependent on the command backend.
    key: str

    # Timestamp in milliseconds since the Unix epoch.
    timestamp_ms: int


class BaseController(abc.ABC):
    """
    Base class for a DuraPy controller, which has a lifespan over some number of commands within DuraPy. A common
    pattern for experiments is to have an initiating command issued either automatically or by an experimenter (e.g.
    "initiate session"), then a number of trials or experiments are performed, and then eventually that "session" is
    terminated. A DuraPy controller can be used to span a set of commands by designating "initiating" and "deleting"
    commands that initiate and delete the controller, respectively. Any commands marked as "controller methods" (i.e.
    registered via #register_controller_method) can then be called on the currently live controller instance.

    Note that there is a stop() method on this interface, as the process can be terminated via SIGTERM or ctrl-c
    at any time; in those cases, stop() will be called.
    """
    @abc.abstractmethod
    def __init__(self, initiating_command: CommandT, context: 'Context'):
        """
        Called when a command registered as a "controller creating" command occurs. Creates a new instance of this
        controller. Assumes that the class type is passed as a controller-creating method.
        """
        ...

    @abc.abstractmethod
    def stop(self, context: 'Context'):
        """
        Handles graceful stopping of a process. Called if a SIGTERM or Ctrl-C is received by the process.
        """
        ...


@dataclasses.dataclass
class Context:
    """
    Contains ongoing context about this process. This context instance is updated appropriately through the process
    lifecycle and passed to any methods responding to commands.
    """

    # Callable that sends a command. Used via #send_command(...)
    _command_sender: Callable[[BaseCommand], PersistedCommand]

    # Current key of the command being processed.
    command_key: Optional[str] = None

    # Current timestamp (according to the command database backend) of the command being processed.
    command_timestamp_ms: Optional[int] = None

    # The current instance maintained by the process infrastructure.
    current_instance: Optional[BaseController] = None

    # A list of persisted commands processed by this process, in *ascending* order (i.e. the first command is first).
    past_commands: List[PersistedCommand] = dataclasses.field(default_factory=list)

    def send_command(self, command: BaseCommand) -> PersistedCommand:
        return self._command_sender(command)


class LifecycleListener(abc.ABC):
    """
    General interface for listening on lifecycle events (e.g. starting up, heartbeats, etc.). Useful for marking
    process health or status.
    """
    @abc.abstractmethod
    def on_started_up(self):
        pass

    @abc.abstractmethod
    def on_heartbeat(self):
        pass
