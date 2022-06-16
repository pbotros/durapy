import logging
import threading


class LoggingThread(threading.Thread):
    """
    Thread that captures exceptions and logs them to a file. See
    http://benno.id.au/blog/2012/10/06/python-thread-exceptions.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._real_run = self.run
        self.run = self._wrap_run

    def _wrap_run(self):
        try:
            self._real_run()
        except:
            logging.exception('Exception during LoggingThread:')
