import logging

from durapy.command.command import CommandRegistry
from durapy.command.model import BaseController, Context
from durapy.command.runner import ProcessRunner
from durapy.command.threading import LoggingThread
from example.commands import TestCommandInitiateSession, TestCommandEndSession, TestCommandPrint, \
    TestCommandNoop, CONFIGURATION, TestCommandIncrement


class ExampleController(BaseController):
    def __init__(self, initiate: TestCommandInitiateSession, context: Context):
        self._name = initiate.name
        self._counter = 0
        context.send_command(TestCommandPrint('Hello world!'))

    def increment(self, increment_command: TestCommandIncrement, context: Context):
        self._counter += 1
        logging.info(f'Counter now at: {self._counter} .')

    def end_session(self, end: TestCommandEndSession, context: Context):
        logging.info('Ending session.')

    def stop(self, context: Context):
        logging.info('Stopping process.')


def print_command(print_command: TestCommandPrint, context: Context):
    logging.info(f'[static print] {print_command.msg}')


def main_test_listener():
    registry = (
        CommandRegistry()
        .register_controller_creator(
            command_class=TestCommandInitiateSession,
            controller_creator=ExampleController)
        .register_controller_method(
            command_class=TestCommandIncrement,
            controller_method=ExampleController.increment)
        .register_controller_deleter(
            command_class=TestCommandEndSession,
            controller_method=ExampleController.end_session)
        .register_static_method(
            command_class=TestCommandPrint,
            method=print_command)
        # Intentionally leaving out TestCommandNoop to demonstrate a message being ignored
    )

    runner = ProcessRunner(
        configuration=CONFIGURATION,
        process_name='test_process',
        command_registry=registry)

    # Normally, we'd just do a runner.run() to run, but since this is a test, we want to send commands to the running
    # process. So we first spawn and start a thread to do so, and then call runner.run(). We then invoke runner.stop()
    # manually when done, whereas typically it'd be handled via a SIGTERM or Ctrl-C.

    def _send_commands():
        import time
        for _ in range(3):
            time.sleep(1)
            runner.send_command(TestCommandInitiateSession(
                name='session-name',
            ))
            runner.send_command(TestCommandPrint(
                msg='to-print'
            ))
            runner.send_command(TestCommandNoop(
                msg='should be ignored since unregistered in registry',
            ))
            runner.send_command(TestCommandEndSession(ended_at=time.time_ns()))
        time.sleep(1)
        runner.stop()
    t = LoggingThread(target=_send_commands)
    t.start()
    runner.run()
    t.join()


if __name__ == '__main__':
    main_test_listener()
