import logging
import os
import platform
import sys
import tempfile
import traceback
from os import path

from fluent import asynchandler as handler
from fluent.handler import FluentRecordFormatter


def log_to_stdout():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    for handler in root.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)


def log_file_for(entry_point):
    if 'GLOG_log_dir' in os.environ:
        tmpdir = os.environ['GLOG_log_dir']
    else:
        tmpdir = '/tmp' if platform.system() == 'Darwin' else tempfile.gettempdir()
    return path.join(tmpdir, f'{entry_point}.log')


def log_to_file(logname: str):
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    log_file = log_file_for(logname)

    print('Logging to ', log_file)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    original_excepthook = sys.excepthook

    def logging_excepthook(type, value, tb):
        logging.exception(traceback.format_tb(tb)[0])
        original_excepthook(type, value, tb)

    sys.excepthook = logging_excepthook


def log_to_fluentd(process_name, fluentd_host: str, fluentd_port: int):
    custom_format = {
        'host': '%(hostname)s',
        'where': '%(module)s.%(funcName)s',
        'type': '%(levelname)s',
        'stack_trace': '%(exc_text)s'
    }

    l = logging.getLogger()
    # We only log via FluentD to enable real-time "tailing" of logs, so it's okay to end up with dropped log messages.
    # Because of this, we use the AsyncFluentHandler, with queue_circular=True, which will drop messages if the buffer
    # becomes too full (i.e. in the case of network partition, heavy traffic, or if the fluentd collector isn't running.
    h = handler.FluentHandler(f'process.{process_name}', host=fluentd_host, port=fluentd_port, queue_circular=True)
    formatter = FluentRecordFormatter(custom_format)
    h.setFormatter(formatter)
    l.addHandler(h)
    return h
