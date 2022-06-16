import logging
from typing import Optional, Awaitable

import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.websocket


class JsonHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.json_args = None

    def prepare(self) -> Optional[Awaitable[None]]:
        if 'Content-Type' in self.request.headers and self.request.headers['Content-Type'] == 'application/json':
            if len(self.request.body) == 0:
                self.json_args = None
                logging.debug("No message in body!")
            else:
                self.json_args = tornado.escape.json_decode(self.request.body)
            self.set_header('Content-Type', 'application/json')
        else:
            self.json_args = None
        return None
