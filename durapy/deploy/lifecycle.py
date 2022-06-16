import logging
import os
import platform
import subprocess
import tempfile
import stat
import uuid
from string import Template
from typing import Tuple, Optional, Dict

from durapy.deploy.target import DeployTarget


def update(target: DeployTarget) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Updates a given target by pulling its underlying git repo. Does this via SSHing and issuing a git pull (see
    ssh_update.sh/ssh_update.bat).
    """
    cmd = None
    ssh_update = None
    if platform.system() == 'Windows':
        if target.ssh_jump_hostname is not None:
            raise NotImplementedError('ssh jump not implemented')
        ssh_update = os.path.join(_resources(), 'ssh_update.bat')
    else:
        if target.ssh_jump_hostname is not None:
            mapping = {'jump_port': str(target.ssh_jump_port),
                       'jump_username': target.ssh_jump_username,
                       'jump_hostname': target.ssh_jump_hostname,
                       'identity_key': target.ssh_identity_key,
                       'username': target.ssh_username,
                       'hostname': target.ssh_hostname,
                       'target_name': target.name}
            cmd = _write_template(target, 'ssh_jump_update.sh.template', mapping=mapping)
        else:
            ssh_update = os.path.join(_resources(), 'ssh_update.sh')

    if cmd is None and ssh_update is not None:
        cmd = [
            ssh_update,
            target.ssh_username,
            target.ssh_hostname,
            str(target.ssh_port),
            target.name]
        logging.info('Issuing command: {}'.format(cmd))
    else:
        logging.info('Running script: {}'.format(cmd))

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    outs, errs = p.communicate()
    if outs is not None:
        outs = outs.decode('utf-8')
    if errs is not None:
        errs = errs.decode('utf-8')

    return p.returncode == 0, outs, errs


def start(target: DeployTarget) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Starts a deploy target via systemctl. See ssh_systemctl.bat/ssh_systemctl.sh.
    """
    return _systemctl_cmd(target, 'start')


def stop(target: DeployTarget) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Stops a deploy target via systemctl. See ssh_systemctl.bat/ssh_systemctl.sh.
    """
    return _systemctl_cmd(target, 'stop')


def restart(target: DeployTarget) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Restarts a deploy target via systemctl. See ssh_systemctl.bat/ssh_systemctl.sh.
    """
    return _systemctl_cmd(target, 'restart')


def _systemctl_cmd(target: DeployTarget, systemctl_cmd: str):
    cmd = None
    ssh_systemctl = None
    if platform.system() == 'Windows':
        ssh_systemctl = os.path.join(_resources(), 'ssh_systemctl.bat')
    else:
        if target.ssh_jump_hostname is not None:
            mapping = {'jump_port': str(target.ssh_jump_port),
                       'jump_username': target.ssh_jump_username,
                       'jump_hostname': target.ssh_jump_hostname,
                       'identity_key': target.ssh_identity_key,
                       'username': target.ssh_username,
                       'hostname': target.ssh_hostname,
                       'target_name': target.name,
                       'systemctl_cmd': systemctl_cmd}
            cmd = _write_template(target, 'ssh_jump_systemctl.sh.template', mapping=mapping)
        else:
            ssh_systemctl = os.path.join(_resources(), 'ssh_systemctl.sh')

    if cmd is None and ssh_systemctl is not None:
        cmd = [
            ssh_systemctl,
            systemctl_cmd,
            target.ssh_username,
            target.ssh_hostname,
            str(target.ssh_port),
            target.name
        ]
        logging.info('Issuing command: {}'.format(cmd))
    else:
        logging.info('Running script: {}'.format(cmd))

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    outs, errs = p.communicate()
    if outs is not None:
        outs = outs.decode('utf-8')
    if errs is not None:
        errs = errs.decode('utf-8')

    return p.returncode == 0, outs, errs


def _resources() -> str:
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources')


def _write_template(target, template_name: str, mapping: Dict, suffix='sh') -> str:
    ssh_jump_update_path = os.path.join(_resources(), template_name)
    with open(ssh_jump_update_path, 'r') as template:
        script = Template(template.read()).substitute(mapping)
    cmd = os.path.join(tempfile.gettempdir(),
                       f"{target.name}_{str(uuid.uuid4())}_{template_name.split('.')[0]}.{suffix}")
    with open(cmd, 'w') as f:
        f.write(script)
    st = os.stat(cmd)
    os.chmod(cmd, st.st_mode | stat.S_IEXEC)
    return cmd
