import logging
import queue
import time
import uuid

from pingpong.commands import InitiateSessionCommand, PingCommand, CONFIGURATION, PongCommand, EndSessionCommand
from durapy.command.command import CommandRegistry
from durapy.command.threading import LoggingThread
from durapy.command.runner import ProcessRunner
from durapy.command.model import BaseController, Context


class Pinger(BaseController):
    def __init__(self, initiate: InitiateSessionCommand, context: Context):
        self._prefix = initiate.prefix
        self._is_running = True
        self._pending_pings = queue.Queue()

        self._pinger_thread = LoggingThread(target=self._ping_forever, args=(context,))
        self._pinger_thread.start()

    def _ping_forever(self, context: Context):
        while self._is_running:
            ping_key = f'{self._prefix}-{str(uuid.uuid4())}'
            logging.info(f'Sending ping: {ping_key}.')
            self._pending_pings.put_nowait(ping_key)
            context.send_command(PingCommand(
                key=ping_key,
            ))
            time.sleep(3)

    def handle_pong(self, pong: PongCommand, context: Context):
        try:
            pending_ping = self._pending_pings.get_nowait()
        except queue.Empty:
            logging.warning(f'Received unsolicited pong? key={pong.input_key}.')
            return

        if pending_ping == pong.input_key:
            logging.info(f'PING/PONG matched on key={pong.input_key}. Output key={pong.output_key}.')

    def handle_end_session(self, command: EndSessionCommand, context: Context):
        self.stop(context)

    def stop(self, context: Context):
        self._is_running = False
        self._pinger_thread.join()


if __name__ == '__main__':
    registry = (
        CommandRegistry()
        .register_controller_creator(
            command_class=InitiateSessionCommand,
            controller_creator=Pinger)
        .register_controller_method(
            command_class=PongCommand,
            controller_method=Pinger.handle_pong)
        .register_controller_deleter(
            command_class=EndSessionCommand,
            controller_method=Pinger.handle_end_session)
    )

    runner = ProcessRunner(
        configuration=CONFIGURATION,
        process_name='pinger',
        command_registry=registry)
    runner.run()
