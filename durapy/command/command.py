import dataclasses
import logging
from typing import TypeVar, Generic, Optional, Any, Callable, Type, Dict

from more_itertools import only  # type: ignore

from durapy.command.model import BaseCommand, BaseController, Context
from durapy.config import Configuration

_ControllerT = TypeVar('_ControllerT', bound='BaseController')
_CommandT = TypeVar('_CommandT', bound='BaseCommand')


class CommandRegistry:
    """
    One of the main interaction class for those implementing services with DuraPy. The CommandRegistry class stores the
    mapping between a command type and the method that will handle that command.

    At its core, the CommandRegistry handles an incoming command depending on the command type. By default, all commands
    are simply ignored. To handle a command with an arbitrary Python function, you can register that command type with
    #register_static_method, passing in the function pointer you want called.

    A common pattern for experiments is to have an initiating command issued either automatically or by an experimenter
    (e.g. "initiate session"), then a number of trials or experiments are performed, and then eventually that "session"
    is terminated. Thus, for convenience, DuraPy provides the concept of a "controller" (inheriting from type
    BaseController) that spans a set of commands. A controller is created from a designated method registered with
    #register_controller_creator, which takes in a designated command and context and returns an instance of that
    controller. While a controller remains live, you can map commands to call methods on this controller instance
    via #register_controller_method, and when the controller instance should be deleted (e.g. at the end of one animal's
    experiments for the day), a command can be registered as a controller deleter via #register_controller_deleter.

    Note that any of these methods can perform any functionality necessary. However, further commands will not be
    processed until processing of a prior command returns. Thus, if a long-running computation  or polling (e.g. if
    continuously monitoring from a sensor) is necessary to perform, it is recommended to put this work in a new thread
    and return quickly.

    For examples, see the included `example` or `pingpong` examples on how to use this.
    """
    def __init__(self):
        self._registered_handlers: Dict[Type[_CommandT], _RegisteredHandler] = {}

    def register_static_method(
            self,
            command_class: Type[_CommandT],
            method: Callable[[_CommandT, Context], Any]):
        if not issubclass(command_class, BaseCommand):
            raise ValueError(f'Did not pass a valid command class; passed {command_class}.')

        # Use default args to capture the arg
        def _method(_: Optional[_ControllerT], command: _CommandT, context: Context, h=method):
            return h(command, context)

        self._registered_handlers[command_class] = _RegisteredHandler(
            command_class=command_class,
            method=_method,
            is_controller_method=False,
            returns_instance=False,
            deletes_instance=False,
        )
        return self

    def register_controller_creator(
            self,
            command_class: Type[_CommandT],
            controller_creator: Callable[[_CommandT, Context], BaseController]):
        if not issubclass(command_class, BaseCommand):
            raise ValueError(f'Did not pass a valid command class; passed {command_class}.')

        # Use default args to capture the arg
        def _method(_: Optional[_ControllerT], command: _CommandT, context: Context, h=controller_creator):
            return h(command, context)

        self._registered_handlers[command_class] = _RegisteredHandler(
            command_class=command_class,
            method=_method,
            is_controller_method=False,
            returns_instance=True,
            deletes_instance=False,
        )
        return self

    def register_controller_method(
            self,
            command_class: Type[_CommandT],
            controller_method: Callable[[_ControllerT, _CommandT, Context], Any]):
        def _method(
                instance: Optional[_ControllerT],
                command: _CommandT,
                context: Context,
                h=controller_method):
            return h(instance, command, context)

        self._registered_handlers[command_class] = _RegisteredHandler(
            command_class=command_class,
            method=_method,
            is_controller_method=True,
            returns_instance=False,
            deletes_instance=False,
        )
        return self

    def register_controller_deleter(
            self,
            command_class: Type[_CommandT],
            controller_method: Callable[[_ControllerT, _CommandT, Context], Any]):
        def _method(
                instance: Optional[_ControllerT],
                command: _CommandT,
                context: Context,
                h=controller_method):
            return h(instance, command, context)

        self._registered_handlers[command_class] = _RegisteredHandler(
            command_class=command_class,
            method=_method,
            is_controller_method=True,
            returns_instance=False,
            deletes_instance=True,
        )
        return self

    def _get_registered_handlers(self):
        return self._registered_handlers.copy()


@dataclasses.dataclass
class _RegisteredHandler(Generic[_ControllerT, _CommandT]):
    command_class: Type[_CommandT]
    method: Callable[[Optional[_ControllerT], _CommandT, Context], Any]
    is_controller_method: bool
    returns_instance: bool
    deletes_instance: bool


class _CommandListener:
    """
    Internal class for handling any incoming commands.
    """
    def __init__(self, configuration: Configuration, registered_handlers: Dict[Type[_CommandT], _RegisteredHandler]):
        self._all_command_classes = configuration.command_classes
        self._registered_handlers = registered_handlers
        self._instance: Optional[BaseController] = None

    def handle_command(self, command: _CommandT, context: Context):
        tup: Optional[_RegisteredHandler] = \
            only([handler for handler_clazz, handler in self._registered_handlers.items() if handler_clazz.type() == command.type()])
        if tup is None:
            logging.info(f'Command type {command.type()} not mapping, ignoring. Command={command}.')
            return

        if not isinstance(command, tup.command_class):
            raise ValueError(f'Mismatched type and command class - is there a duplicate?? '
                             f'command={command}, expected={tup.command_class}')

        if tup.is_controller_method:
            if self._instance is None:
                logging.warning(f'Method for command type {command.type()} is an instance method, '
                                f'but an instance has not been created. Did you forget to invoke or setup a method '
                                f'with returns_instance=True? Ignoring this command.')
                return

            tup.method(self._instance, command, context)
            if tup.deletes_instance:
                logging.info(f'Deleting instance {self._instance}.')
                self._instance = None
        else:
            if tup.returns_instance and self._instance is not None:
                logging.warning(f'Method for command type {command.type()} should be creating an instance, '
                                f'but an instance is already set [{self._instance}]. Ignoring.')
                return
            ret = tup.method(None, command, context)
            if tup.returns_instance:
                self._instance = ret
                logging.info(f'Successfully created instance {self._instance}.')

    def handle_stop(self, context: Context):
        if self._instance is not None:
            self._instance.stop(context)


