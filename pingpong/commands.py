import dataclasses

from durapy.backends.redis import RedisCommandDatabaseFactory
from durapy.command.model import BaseCommand
from durapy.config import Configuration, FluentDConfiguration, DeployConfiguration
from durapy.deploy.status.config import LifecycleDatabaseConfiguration


@dataclasses.dataclass
class InitiateSessionCommand(BaseCommand):
    prefix: str

    @staticmethod
    def type() -> str:
        return 'INITIATE_SESSION'


@dataclasses.dataclass
class PingCommand(BaseCommand):
    key: str

    @staticmethod
    def type() -> str:
        return 'PING'


@dataclasses.dataclass
class PongCommand(BaseCommand):
    input_key: str
    output_key: str

    @staticmethod
    def type() -> str:
        return 'PONG'


@dataclasses.dataclass
class EndSessionCommand(BaseCommand):
    @staticmethod
    def type() -> str:
        return 'END_SESSION'


ALL_COMMAND_CLASSES = [
    InitiateSessionCommand,
    PingCommand,
    PongCommand,
    EndSessionCommand,
]

CONFIGURATION = Configuration(
    command_prefix='pingpong',
    command_db_factory=RedisCommandDatabaseFactory(redis_hostname='127.0.0.1', redis_port=6379),
    command_classes=ALL_COMMAND_CLASSES,
    fluentd=FluentDConfiguration(
        hostname='127.0.0.1',
        port=24224,
        log_file_dir='/tmp/pingpong-logs',
    ),
    deploy=DeployConfiguration(
        lifecycle_database_configuration=LifecycleDatabaseConfiguration(
            db_username='root',
            db_hostname='127.0.0.1',
            db_name='pingpong',
        ),
    )
)
