import os
import uuid

import tornado.web
import tornado.websocket

from example.commands import ALL_COMMAND_CLASSES, TestCommandPrint, TestCommandNested, Nested, CONFIGURATION
from durapy.backends.memory import InMemoryCommandDatabaseFactory
from durapy.config import Configuration
from durapy.webserver.webserver import DurapyWebserver


class CommandsHistoryHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('commands_history.html', active='commands_history',
                    title='Commands History')


class CommandsSendHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('commands_send.html', active='commands_send',
                    title='Send Commands')


class LoggingHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('logging.html', active='logging', title='Logging')

class StatusesHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('statuses.html', active='statuses', title='Statuses')


def main_webserver():
    webserver_dir = os.path.dirname(os.path.realpath(__file__))
    ws = DurapyWebserver(
        webserver_dir=webserver_dir,
        configuration=CONFIGURATION)

    # Seed the webserver with a few commands.
    ws.command_database().send_command(TestCommandPrint(msg='1'))
    ws.command_database().send_command(TestCommandPrint(msg='2'))
    ws.command_database().send_command(TestCommandNested(upper_msg='upper1', nested=Nested(lower_msg='lower1')))

    app = ws.new_application()
    app.add_handlers(
        '.*',
        [
            (r"/", CommandsHistoryHandler),
            (r"/commands/history", CommandsHistoryHandler),
            (r"/commands/send", CommandsSendHandler),
            (r"/logging", LoggingHandler),
            (r"/statuses", StatusesHandler),
            (r'/(favicon.ico)', tornado.web.StaticFileHandler, {"path": os.path.join(webserver_dir, 'static')}),
        ]
    )
    ws.run(app)


if __name__ == '__main__':
    main_webserver()
