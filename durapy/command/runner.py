import logging
import signal
import traceback

from durapy.backends.base import CommandDatabase
from durapy.command._logging import log_to_stdout, log_to_file, log_to_fluentd
from durapy.command.command import CommandRegistry, _RegisteredHandler, _CommandListener, _CommandT
from durapy.command.model import PersistedCommand, Context
from durapy.config import Configuration
from durapy.deploy.status.status import ProcessStatusDatabase


class ProcessRunner:
    """
    Main runner for any DuraPy processes. This fetches commands from the relevant database and passes the right
    commands to the registered methods.

    This is expected to be used as:

    ```
        if __name__ == "__main__":
            ProcessRunner(<...args...>).run()
    ```

    which will block forever until the process is terminated (e.g. SIGTERM or ctrl-C).
    """

    def __init__(self,
                 configuration: Configuration,
                 process_name: str,
                 command_registry: CommandRegistry,
                 override_signal_handlers: bool = True):
        log_to_stdout()
        log_to_file(process_name)
        if configuration.fluentd is not None:
            self._fluentd_handler = log_to_fluentd(
                process_name, configuration.fluentd.hostname, configuration.fluentd.port)
        else:
            self._fluentd_handler = None

        self._process_name = process_name

        # Fill in no-ops for all command classes
        registered_handlers = command_registry._get_registered_handlers()
        for clazz in configuration.command_classes:
            if clazz in registered_handlers:
                continue
            registered_handlers[clazz] = _RegisteredHandler(
                command_class=clazz,
                method=lambda *args, clazz_type=clazz.type(), **kwargs: logging.info(f'Ignoring command of type {clazz_type}.'),
                is_controller_method=False,
                returns_instance=False,
                deletes_instance=False,
                is_stop_static_method=False,
            )

        self._command_listener = _CommandListener(
            configuration=configuration,
            registered_handlers=registered_handlers
        )
        registered_command_classes = [h.command_class for h in registered_handlers.values()]
        self._command_db: CommandDatabase = configuration.command_db_factory.create(
            configuration.command_prefix, registered_command_classes)

        self.is_stopped = False

        if configuration.deploy is not None and configuration.deploy.lifecycle_database_configuration is not None:
            self._lifecycle_listener = ProcessStatusDatabase(
                process_name, configuration.deploy.lifecycle_database_configuration)
        else:
            self._lifecycle_listener = None

        if override_signal_handlers:
            signal.signal(signal.SIGINT, self.stop)
            signal.signal(signal.SIGTERM, self.stop)

    def stop(self, signum=None, frame=None):
        logging.info("BMI process {} received stop signal.".format(self._process_name))
        self.is_stopped = True

    def send_command(self, command: _CommandT) -> PersistedCommand:
        return self._command_db.send_command(command)

    def run(self):
        logging.info("Beginning process {}".format(self._process_name))

        if self._lifecycle_listener is not None:
            self._lifecycle_listener.on_started_up()

        context = Context(_command_sender=self._command_db.send_command)
        print_idx = 0
        try:
            while not self.is_stopped:
                if self._lifecycle_listener is not None:
                    try:
                        self._lifecycle_listener.on_heartbeat()
                    except Exception as e:
                        logging.warning('Marking heartbeat failed, hopefully transient error. Continuing. '
                                        'exception={}'.format(e))

                command = self._command_db.fetch_next(1000)
                if command is None:
                    print_idx += 1
                    if print_idx < 10:
                        logging.info("[Process {}] No commands found to process.".format(self._process_name))
                    elif print_idx == 10:
                        logging.info(
                            "[Process {}] No commands found to process. Not printing anymore.".format(
                                self._process_name))
                    continue

                logging.info("[Process {}] Fetched command: {}".format(self._process_name, command))
                context.command_key = command.key
                context.command_timestamp_ms = command.timestamp_ms
                self._command_listener.handle_command(command.command, context)
                context.past_commands.append(command)
            # Fall through to `finally` block, where handle_stop() is called.
        except Exception as e:
            logging.error('ProcessRunner [process {}] caught exception: {}. Traceback:'.format(self._process_name, e))
            logging.error(traceback.format_exc())
            raise e
        finally:
            try:
                context.command_key = None
                context.command_timestamp_ms = None
                self._command_listener.handle_stop(context)

                # Always execute #handle_stop(), even if the above calls throw exceptions.
                logging.info('ProcessRunner [process {}] stopped.'.format(self._process_name))
            finally:
                # Always execute #close() here, even if the above throw exceptions
                if self._fluentd_handler is not None:
                    self._fluentd_handler.close()
