import dataclasses
from typing import List, Type, Optional

from durapy.backends.base import CommandDatabaseFactory
from durapy.deploy.status.config import LifecycleDatabaseConfiguration
from durapy.deploy.target import DeployTarget
from durapy.command.model import BaseCommand


@dataclasses.dataclass
class Configuration:
    """
    Global configuration shared across all processes for a given experiment or namespace. The same configuration should
    be used for each process, so it's recommended to put this somewhere shared for each process to use without
    duplicating code.
    """

    # Prefix for all commands sent. Use this to namespace different sets or iterations of experiments, especially if
    # there are two sets of processes running simultaneously that should be separate from one another. All processes
    # that need to communicate with one another must have the same command prefix. Do not change this unless you're
    # okay with starting from a blank slate.
    command_prefix: str

    # Instance of `CommandDatabaseFactory` that corresponds to the implementation of reading and writing commands
    # sent to processes. The recommended database factory to use is `RedisCommandDatabaseFactory`, which utilizes
    # Redis as a database. Do not change this unless you're okay with starting from a blank state.
    command_db_factory: CommandDatabaseFactory

    # A list of all known command types. Used to encode/decode commands that are sent between processes. For historical
    # purposes, try not to remove any commands after using it, and try not to change command types. If you do either,
    # historical commands might fail to parse, and those commands may disappear from your history.
    command_classes: List[Type[BaseCommand]]

    # Optional. Deployment-related configuration, including details of where your processes are running and if/how
    # their running status should be tracked.
    deploy: Optional['DeployConfiguration'] = None

    # Optional. Configuration of the fluentd daemon, if log tailing is desired for the webserver. This must
    # correspond to the same machine running the webserver.
    fluentd: Optional['FluentDConfiguration'] = None

@dataclasses.dataclass
class DeployConfiguration:
    # Optional. Configuration details on the database used to track lifecycle updates, if desired.
    lifecycle_database_configuration: Optional[LifecycleDatabaseConfiguration] = None

    # A list of the known deploy targets, i.e. descriptions of the machines on which each process lives. This is not
    # strictly required, but is recommended to enable GUI control of each individual's process deployment (e.g.
    # restarting processes, updating them, setting them up in systemctl, etc.).
    deploy_targets: List[DeployTarget] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class FluentDConfiguration:
    # The hostname/port of the fluentd daemon, if log tailing is desired for the webserver. This must
    # correspond to the same machine running the webserver.
    hostname: str
    port: int

    # The log file directory to which fluentd outputs. Should exactly match the directory given in the `td-agent.conf`
    # configuration file used by fluentd. Again, needs to be accessible on the same machine running the webserver.
    # Preferably, give the absolute filename (e.g. /path/to/foo) rather than relative (e.g. ./foo).
    log_file_dir: str

    # The "tail" executable to call for tailing fluentd output. Can specify full path if needed by overriding this.
    tail_bin: str = 'tail'
