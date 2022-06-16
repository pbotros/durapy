import dataclasses


@dataclasses.dataclass
class LifecycleDatabaseConfiguration:
    """
    Encapsulates configuration necessary to write lifecycle updates to a database. Assumes MySQL database.

    The database provided should have a table calling `process_statuses` matching that found in `status_schema.sql`.
    """
    db_username: str
    db_hostname: str
    db_name: str
    db_port: int = 3306
    db_password: str = ''
