import dataclasses
import datetime
import subprocess
from typing import Optional, List

import sqlalchemy
from dataclasses_json import DataClassJsonMixin
from durapy.command.model import LifecycleListener
from durapy.deploy.status.config import LifecycleDatabaseConfiguration


@dataclasses.dataclass
class ProcessStatus(DataClassJsonMixin):
    """
    Describes the current status of a running process.
    """
    process_name: str
    last_started_at: datetime.datetime
    last_started_ago: int
    last_heartbeat_at: datetime.datetime
    last_heartbeat_ago: int
    git_sha: str


class ProcessStatusDatabase(LifecycleListener):
    db: sqlalchemy.Engine

    def __init__(
            self,
            process_name: Optional[str],
            config: LifecycleDatabaseConfiguration):
        """
        :param process: the process for which to mark heartbeats / restarts. Leave as None if just fetching.
        """
        self.db = sqlalchemy.create_engine(
            f'mysql+pymysql://'
            f'{config.db_username}:{config.db_password}'
            f'@{config.db_hostname}:{config.db_port}/{config.db_name}',
            pool_pre_ping=True)
        self._sha = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip()
        self._process_name = process_name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db = None

    def fetch_all(self) -> List[ProcessStatus]:
        with self.db.begin() as conn:
            rows = conn.execute(sqlalchemy.text(
                'SELECT '
                '  *'
                ', CURRENT_TIMESTAMP() - last_heartbeat_at as last_heartbeat_ago '
                ', CURRENT_TIMESTAMP() - last_started_at as last_started_ago '
                'FROM process_statuses '
                'ORDER BY process_name ASC'))
        ret = []
        for row in rows.mappings():
            ret.append(ProcessStatus(
                process_name=row['process_name'],
                last_started_at=row['last_started_at'],
                last_started_ago=int(row['last_started_ago']),
                last_heartbeat_at=row['last_heartbeat_at'],
                last_heartbeat_ago=int(row['last_heartbeat_ago']),
                git_sha=row['git_sha'],
            ))
        return ret

    def on_started_up(self):
        s = 'INSERT INTO process_statuses ' \
            '(process_name, last_started_at, last_heartbeat_at, git_sha) VALUES ' \
            '(:process_name, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), :git_sha) ' \
            'ON DUPLICATE KEY UPDATE ' \
            '  process_name = :process_name ' \
            ', last_started_at = CURRENT_TIMESTAMP()' \
            ', last_heartbeat_at = CURRENT_TIMESTAMP()' \
            ', git_sha = :git_sha'
        with self.db.begin() as conn:
            conn.execute(sqlalchemy.text(s),
                         dict(process_name=self._process_name, git_sha=self._sha))

    def on_heartbeat(self):
        s = 'UPDATE process_statuses SET ' \
            '  last_heartbeat_at = CURRENT_TIMESTAMP()' \
            'WHERE process_name = :process_name'
        with self.db.begin() as conn:
            conn.execute(sqlalchemy.text(s), dict(process_name=self._process_name))
