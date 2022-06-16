import logging

from pingpong.commands import InitiateSessionCommand, PingCommand, CONFIGURATION, PongCommand, EndSessionCommand
from durapy.command.command import CommandRegistry
from durapy.command.runner import ProcessRunner
from durapy.command.model import BaseController, Context


class Ponger(BaseController):
    def __init__(self, initiate: InitiateSessionCommand, context: Context):
        self._expected_prefix = initiate.prefix

    def handle_ping(self, ping: PingCommand, context: Context):
        input_key = ping.key
        if not input_key.startswith(self._expected_prefix):
            logging.warning('Ping received with incorrect prefix.')
            return

        output_key = input_key[::-1]
        context.send_command(PongCommand(
            input_key=input_key,
            output_key=output_key
        ))

    def handle_end_session(self, command: EndSessionCommand, context: Context):
        self.stop(context)

    def stop(self, context: Context):
        pass


if __name__ == '__main__':
    registry = (
        CommandRegistry()
        .register_controller_creator(
            command_class=InitiateSessionCommand,
            controller_creator=Ponger)
        .register_controller_method(
            command_class=PingCommand,
            controller_method=Ponger.handle_ping)
        .register_controller_deleter(
            command_class=EndSessionCommand,
            controller_method=Ponger.handle_end_session)
    )

    runner = ProcessRunner(
        configuration=CONFIGURATION,
        process_name='ponger',
        command_registry=registry)
    runner.run()
