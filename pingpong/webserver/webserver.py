import os

import tornado.web
import tornado.websocket

from pingpong.commands import CONFIGURATION
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
