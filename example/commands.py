import dataclasses
import uuid
from typing import List

from durapy.backends.memory import InMemoryCommandDatabaseFactory
from durapy.command.model import BaseCommand
from durapy.config import Configuration, FluentDConfiguration, DeployConfiguration
from durapy.deploy.status.config import LifecycleDatabaseConfiguration


@dataclasses.dataclass
class TestCommandInitiateSession(BaseCommand):
    name: str

    @staticmethod
    def type() -> str:
        return 'INITIATE_SESSION'


@dataclasses.dataclass
class TestCommandEndSession(BaseCommand):
    ended_at: int

    @staticmethod
    def type() -> str:
        return 'END_SESSION'


@dataclasses.dataclass
class TestCommandIncrement(BaseCommand):
    @staticmethod
    def type() -> str:
        return 'INCREMENT'


@dataclasses.dataclass
class TestCommandPrint(BaseCommand):
    msg: str

    @staticmethod
    def type() -> str:
        return 'PRINT'


@dataclasses.dataclass
class Nested:
    lower_msg: str


@dataclasses.dataclass
class TestCommandNested(BaseCommand):
    upper_msg: str
    nested: Nested

    @staticmethod
    def type() -> str:
        return 'NESTED'


@dataclasses.dataclass
class TestCommandNoop(BaseCommand):
    msg: str

    @staticmethod
    def type() -> str:
        return 'NOOP'

@dataclasses.dataclass
class TestCommandEmpty(BaseCommand):
    @staticmethod
    def type() -> str:
        return 'EMPTY'


@dataclasses.dataclass
class TestCommandComplex(BaseCommand):
    msg_str: str
    msg_int: int
    msg_float: float
    msg_list: List[int]
    msg_nested: Nested
    msg_default: str = 'default_str'

    @staticmethod
    def type() -> str:
        return 'COMPLEX'


ALL_COMMAND_CLASSES = [
    TestCommandInitiateSession,
    TestCommandEndSession,
    TestCommandPrint,
    TestCommandNoop,
    TestCommandNested,
    TestCommandEmpty,
    TestCommandComplex,
    TestCommandIncrement,
]

CONFIGURATION = Configuration(
    # This SHOULD BE CONSTANT in real use cases. We use UUID here to create a new set of test commands each run.
    command_prefix=str(uuid.uuid4()),

    command_db_factory=InMemoryCommandDatabaseFactory(),
    command_classes=ALL_COMMAND_CLASSES,
    fluentd=FluentDConfiguration(
        hostname='127.0.0.1',
        port=24224,
        log_file_dir='/tmp/example-logs',
    ),
    deploy=DeployConfiguration(
        lifecycle_database_configuration=LifecycleDatabaseConfiguration(
            db_username='root',
            db_hostname='127.0.0.1',
            db_name='mubmi_rodents',
        ),
    )
)
