import asyncio
import dataclasses
import functools
import logging
import os
import signal
import pendulum
from asyncio import subprocess
from typing import List, Type, Optional, Callable, Any

import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.websocket
from more_itertools import only

from durapy.backends.base import CommandDatabase, CommandDatabaseFactory
from durapy.command._logging import log_to_stdout, log_to_file
from durapy.command.command import CommandRegistry
from durapy.command.model import BaseCommand, Context
from durapy.command.runner import ProcessRunner
from durapy.config import Configuration, FluentDConfiguration
from durapy.deploy import lifecycle
from durapy.deploy.status.status import ProcessStatusDatabase
from durapy.deploy.target import DeployTarget
from durapy.webserver._inspect import extract_flattened_field_descriptions_class, \
    populate_from_field_descriptions_class, \
    FieldDescriptionForPopulating
from durapy.webserver.json_handler import JsonHandler


class CommandTypesHandler(JsonHandler):
    """
    GET /api/command-types: returns a list of the registered commands for this DuraPy instance. Form of:
    {
        'command_types': [
            {
                'type': <command type>,
                'field_descriptions': [
                    {
                        **<FieldDescription fields>,
                    },
                    ...
                ]
            },
            ...
        ]
    }
    """
    def __init__(
            self,
            *args,
            command_classes: List[Type[BaseCommand]],
            **kwargs):
        super().__init__(*args, **kwargs)
        self._command_classes = command_classes

    def get(self):
        ret = []
        for clazz in self._command_classes:
            field_descriptions = extract_flattened_field_descriptions_class(clazz, existing_instance=None)
            ret.append({
                'type': clazz.type(),
                'field_descriptions': [fd.to_dict(encode_json=True) for fd in field_descriptions],
            })
        return self.write({
            'command_types': ret,
        })


class CommandGetHandler(JsonHandler):
    """
    GET /api/commands/<command key>: finds a command according to its key (found in the PersistedCommand). Returns 404
    if it cannot be found. Otherwise, it returns the similar fields as seen in the GET /api/commands response.
    """
    def __init__(
            self,
            *args,
            command_db: CommandDatabase,
            **kwargs):
        super().__init__(*args, **kwargs)
        self._command_db = command_db

    def get(self, key):
        persisted_command = self._command_db.fetch_by_key(key)
        if persisted_command is None:
            logging.info(f'Could not find key {key}.')
            self.send_error(404)
            return

        d = persisted_command.to_dict(encode_json=True)
        d['type'] = persisted_command.command.type()
        field_descriptions = extract_flattened_field_descriptions_class(
            clazz=persisted_command.command.__class__,
            existing_instance=persisted_command.command)
        d['field_descriptions'] = [fd.to_dict(encode_json=True) for fd in field_descriptions]
        return self.write({
            'command': d
        })


class CommandCrudHandler(JsonHandler):
    """
    CRUD-style API handle for creating/listing DuraPy commands.
        GET /api/commands: returns a json response with key 'commands', where each element has the structure:
            [
                {
                    **<PersistedCommand fields>,
                    'type': <command_type>,
                    'field_descriptions': [
                        **<FieldDescription fields>,
                    ],
                },
                ...
            ]

        POST /api/commands: expects a json payload that is either a command or a set of field descriptions, i.e.:
            {
                'type': <command type>,
                'command': {
                    <command fields>,
                },
            }
            OR
            {
                'type': <command type>,
                'field_descriptions': [
                    {
                        **<FieldDescription fields>,
                    },
                ],
            }
    """
    def __init__(
            self,
            *args,
            command_db: CommandDatabase,
            command_classes: List[Type[BaseCommand]],
            **kwargs):
        super().__init__(*args, **kwargs)
        self._command_db = command_db
        self._command_classes = command_classes

    def get(self):
        num = int(self.get_argument('num', default=str(10)))
        offset = int(self.get_argument('offset', default=str(0)))

        last_persisted_commands = self._command_db.fetch_last(num, offset=offset)
        response_commmands = []
        for persisted_command in last_persisted_commands:
            d = persisted_command.to_dict(encode_json=True)
            d['type'] = persisted_command.command.type()
            field_descriptions = extract_flattened_field_descriptions_class(
                clazz=persisted_command.command.__class__,
                existing_instance=persisted_command.command)
            d['field_descriptions'] = [fd.to_dict(encode_json=True) for fd in field_descriptions]

            response_commmands.append(d)
        return self.write({
            'commands': response_commmands
        })

    def post(self):
        if 'type' not in self.json_args:
            logging.info(f'Could not find key "type" in command to send? Command={self.json_args}')
            self.send_error(400)
            return

        clazz = only([c for c in self._command_classes if c.type() == self.json_args['type']])
        if clazz is None:
            logging.info(f'Could not find matching class {self.json_args["type"]} in registered command classes? '
                         f'Registered: {self._command_classes}')
            self.send_error(400)
            return

        if 'command' in self.json_args:
            command_to_send = self._from_command(clazz)
        elif 'field_descriptions' in self.json_args:
            command_to_send = self._from_field_descriptions(clazz)
        else:
            logging.info(f'Invalid format when attempting to create a new command. params={self.json_args}')
            self.send_error(400)
            return

        sent = self._command_db.send_command(command_to_send)
        logging.info('Sent command: {}'.format(sent))
        d = sent.to_dict(encode_json=True)
        d['type'] = command_to_send.type()
        return self.write({
            'command': d
        })

    def _from_command(self, clazz: Type[BaseCommand]) -> BaseCommand:
        command_dict = self.json_args['command']
        return clazz.from_dict(command_dict)

    def _from_field_descriptions(self, clazz: Type[BaseCommand]) -> BaseCommand:
        fds = [FieldDescriptionForPopulating.from_dict(d) for d in self.json_args['field_descriptions']]
        return populate_from_field_descriptions_class(clazz, fds)


class TailWebSocketHandler(tornado.websocket.WebSocketHandler):
    """
    Websocket handler for displaying aggregated logs across your services. Once the websocket is open, this will
    write back log lines, with 1 log line (delimited by a newline) per message. This is only used if there is a
    FluentDConfiguration configured so DuraPy knows where to find the aggregated logs.
    """

    def __init__(self, *args, fluentd_config: FluentDConfiguration, **kwargs):
        super(TailWebSocketHandler, self).__init__(*args, **kwargs)
        self._fluentd_config = fluentd_config
        self._process = None
        self._closing = False

    async def open(self):
        if self._fluentd_config is None:
            return

        # Not sure how this would happen, but just in case
        if self._process is not None:
            self._process.terminate()
            self._process.wait()
            self._process = None

        self._process = await subprocess.create_subprocess_shell(
            f'{self._fluentd_config.tail_bin} -n 100 -F {self._fluentd_config.log_file_dir}/*log',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        tornado.ioloop.IOLoop.current().spawn_callback(self._forward_messages)

    async def _forward_messages(self):
        try:
            while True:
                if self._closing:
                    break

                retcode = self._process.returncode
                if retcode is not None:
                    logging.info('Process exited: stdout/stderr:')
                    stdout, stderr = await self._process.communicate()
                    logging.info(stdout)
                    logging.info(stderr)
                    break

                try:
                    # Read lines output by our fluentd logging aggregation daemon
                    line = await asyncio.wait_for(self._process.stdout.readline(), 0.1)
                    await self.write_message(line)
                except asyncio.TimeoutError:
                    pass
        finally:
            self.close()

            # And then if it hasn't already exited, kill it
            if self._process.returncode is None:
                self._process.terminate()
                logging.info('Tail process terminating.')
                return await self._process.wait()  # Wait for the child process to exit

    def on_close(self):
        self._closing = True


class CompositeStaticFileHandler(tornado.web.StaticFileHandler):
    """
    Extension of Tornado's StaticFileHandler that searches in both its normally configured static path and the static
    path bundled with this DuraPy installation.
    """
    @classmethod
    def get_absolute_path(cls, root: str, path: str) -> str:
        # Look in either the given root, OR in the default static
        ret = super(CompositeStaticFileHandler, cls).get_absolute_path(root, path)
        if os.path.exists(ret):
            return ret

        ret = super(CompositeStaticFileHandler, cls).get_absolute_path(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static'), path)
        return ret

    def validate_absolute_path(self, root: str, absolute_path: str) -> Optional[str]:
        try:
            return super(CompositeStaticFileHandler, self).validate_absolute_path(root, absolute_path)
        except tornado.web.HTTPError:
            return super(CompositeStaticFileHandler, self).validate_absolute_path(
                os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static'), absolute_path)


class DeployGetHandler(JsonHandler):
    """
    Returns the current status of the various configured services.
    GET /api/deploy returns:
    {
        'statuses': [
            {
                **ProcessStatus fields,
            },
            ...
        ],
    }
    """
    def __init__(self, *args, configuration: Configuration, **kwargs):
        super(DeployGetHandler, self).__init__(*args, **kwargs)
        if configuration.deploy is not None and configuration.deploy.lifecycle_database_configuration is not None:
            self._config = configuration.deploy.lifecycle_database_configuration
            self._target_processes = [t.name for t in configuration.deploy.deploy_targets]
        else:
            self._config = None
            self._targets = []

    def get(self):
        if self._config is None:
            return self.write({
                'statuses': []
            })

        with ProcessStatusDatabase(process_name=None, config=self._config) as db:
            fetched = db.fetch_all()

        statuses = []
        for f in fetched:
            f = f.to_dict(encode_json=True)
            f['last_started_at'] = pendulum.from_timestamp(f['last_started_at'], 'UTC').isoformat()
            f['last_heartbeat_at'] = pendulum.from_timestamp(f['last_heartbeat_at'], 'UTC').isoformat()
            f['target_configured'] = f['process_name'] in self._target_processes
            statuses.append(f)
        return self.write({
            'statuses': statuses
        })


class _LifecycleHandler(JsonHandler):
    def __init__(self, *args, lifecycle_cmd: Callable[[DeployTarget], Any], configuration: Configuration, **kwargs):
        super(_LifecycleHandler, self).__init__(*args, **kwargs)
        self._cmd = lifecycle_cmd
        if configuration.deploy is not None:
            self._targets = configuration.deploy.deploy_targets
        else:
            self._targets = []

    def post(self, target_name: str):
        target = only([t for t in self._targets if t.name == target_name])
        if target is None:
            self.write_error(404)
            return

        success, outs, errs = self._cmd(target)
        logging.info(f'Success: {success}, outs={outs}, errs={errs}')
        return self.write({
            'success': success,
            'outs': outs,
            'errs': errs,
        })


class DeployUpdateHandler(_LifecycleHandler):
    def __init__(self, *args, configuration: Configuration, **kwargs):
        super(DeployUpdateHandler, self).__init__(
            *args, lifecycle_cmd=lifecycle.update, configuration=configuration, **kwargs)


class DeployStartHandler(_LifecycleHandler):
    def __init__(self, *args, configuration: Configuration, **kwargs):
        super(DeployStartHandler, self).__init__(
            *args, lifecycle_cmd=lifecycle.start, configuration=configuration, **kwargs)


class DeployRestartHandler(_LifecycleHandler):
    def __init__(self, *args, configuration: Configuration, **kwargs):
        super(DeployRestartHandler, self).__init__(
            *args, lifecycle_cmd=lifecycle.restart, configuration=configuration, **kwargs)


class DeployStopHandler(_LifecycleHandler):
    def __init__(self, *args, configuration: Configuration, **kwargs):
        super(DeployStopHandler, self).__init__(
            *args, lifecycle_cmd=lifecycle.stop, configuration=configuration, **kwargs)


class _StaticCommandDatabaseFactory(CommandDatabaseFactory):
    """
    Command database factory that just returns the instance passed to it. Useful to ensure both the webserver
    and the DuraPy infrastructure share the exact same database instance.
    """
    def __init__(self, db):
        self._db = db

    def create(self, command_prefix: str, command_classes: List[Type[BaseCommand]]) -> CommandDatabase:
        return self._db

class DurapyWebserver:
    def __init__(
            self,
            webserver_dir: str,
            configuration: Configuration,
            registry: CommandRegistry = None,
            webserver_port: int = 5001):
        """
        @param webserver_dir: the directory containing static/ and templates/ directory, which contain css/js/img files
        and the HTML template files, respectively. This directory will be searched in addition to durapy's static/
        directory when finding static files. A traditional value for this would be
        `os.path.dirname(os.path.realpath(__file__))` from the calling file.
        @param registry: a command registry to be registered for this webserver. Useful for making this webserver
        also be able to respond to commands like any other DuraPy service.
        @param webserver_port: port on which to listen for the Tornado HTTP webserver.
        """
        self._webserver_dir = webserver_dir
        self._webserver_port = webserver_port
        self._command_prefix = configuration.command_prefix
        if registry is not None:
            self._registry = registry
        else:
            self._registry = CommandRegistry()

        self._command_db = configuration.command_db_factory.create(
            command_prefix=configuration.command_prefix,
            command_classes=configuration.command_classes)
        self._configuration = dataclasses.replace(
            configuration,
            command_db_factory=_StaticCommandDatabaseFactory(self._command_db))
        self._command_classes = configuration.command_classes
        self._fluentd_config = configuration.fluentd

    def command_database(self) -> CommandDatabase:
        return self._command_db

    def new_application(self) -> tornado.web.Application:
        """
        Creates a new Tornado application, suitable for extending according to the use case.

        By default, the returned application binds up a number of JSON-based and websocket handlers that perform some
        basic DuraPy operations. See the below handlers and their linked classes for built-in functionality, or see
        the example webserver on how to use these.
        """
        return tornado.web.Application(
            handlers=[
                # API methods
                (r"/api/commands", CommandCrudHandler, dict(
                    command_db=self._command_db,
                    command_classes=self._command_classes,
                )),
                (r"/api/commands/([^/]+)", CommandGetHandler, dict(
                    command_db=self._command_db,
                )),
                (r"/api/command-types", CommandTypesHandler, dict(
                    command_classes=self._command_classes,
                )),
                (r"/api/deploy", DeployGetHandler, dict(configuration=self._configuration)),
                (r"/api/deploy/([A-Za-z_-]*)/update", DeployUpdateHandler, dict(configuration=self._configuration)),
                (r"/api/deploy/([A-Za-z_-]*)/start", DeployStartHandler, dict(configuration=self._configuration)),
                (r"/api/deploy/([A-Za-z_-]*)/restart", DeployRestartHandler, dict(configuration=self._configuration)),
                (r"/api/deploy/([A-Za-z_-]*)/stop", DeployStopHandler, dict(configuration=self._configuration)),
                (r"/ws/tail", TailWebSocketHandler, dict(fluentd_config=self._fluentd_config)),
            ],
            template_path=os.path.join(self._webserver_dir, 'templates'),

            # Store a DuraPy context in the application so it's reachable in handlers if needed.
            durapy_context=Context(_command_sender=self._command_db.send_command),

            # For searching both durapy's static files and the implementation's
            static_handler_class=CompositeStaticFileHandler,
            static_path=os.path.join(self._webserver_dir, 'static'),
            autoreload=True,
            debug=True,
        )

    def run(self, app: tornado.web.Application):
        """
        Runs a tornado application, likely one produced by #new_application(). This will block forever until the
        process is Ctrl-C'd or killed.
        """
        # Don't trap Ctrl+C in the DuraPy process runner, since it's running in the background and makes the whole
        # process unkillable
        runner = ProcessRunner(
            configuration=self._configuration,
            process_name='webserver',
            command_registry=self._registry,
            override_signal_handlers=False)

        http_server = app.listen(self._webserver_port)

        orig_sigint = signal.getsignal(signal.SIGINT)
        orig_sigterm = signal.getsignal(signal.SIGTERM)

        def handler(orig, signum=None, frame=None):
            http_server.stop()
            runner.stop()
            loop = tornado.ioloop.IOLoop.current()
            if loop is not None:
                loop.stop()
            if orig is not None and callable(orig):
                orig(signum, frame)

        signal.signal(signal.SIGINT, functools.partial(handler, orig_sigint))
        signal.signal(signal.SIGTERM, functools.partial(handler, orig_sigterm))

        loop = tornado.ioloop.IOLoop.current()
        loop.run_in_executor(None, runner.run)

        # Finally start the tornado server
        loop.start()
