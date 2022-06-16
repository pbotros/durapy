from dataclasses import dataclass
from typing import Optional


@dataclass
class DeployTarget:
    """
    Details on a deployed "target" in the durapy ecosystem. These details enable remote management of this deploy target,
    such as deploying new versions and restarting the process.

    Assumptions:
        Git repo is present at `git_repo_directory`
        Processes are registered with systemctl on Unix systems.
    """
    name: str
    ssh_username: str
    ssh_hostname: str
    git_repo_directory: str = '~/Development/python'
    ssh_port: int = 22
    ssh_identity_key: Optional[str] = None
    ssh_jump_username: Optional[str] = None
    ssh_jump_hostname: Optional[str] = None
    ssh_jump_port: Optional[int] = None
