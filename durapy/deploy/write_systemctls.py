import dataclasses
import getpass
import os
import pathlib
import sys
import tempfile
from dataclasses import dataclass
from string import Template
from typing import Optional, List, Tuple, Dict


@dataclass
class Systemctl(object):
    script_relative_path: str
    exec_before: Optional[str] = None
    process_name_override: Optional[str] = None
    kill_mode: Optional[str] = "process"
    extra_environments: Dict[str, str] = dataclasses.field(default_factory=dict)


def write(service_prefix: str, relative_path_root: str, systemctls: List[Systemctl]):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(this_dir, 'resources', 'systemctl_template.service'), 'r') as f:
        template_string = f.read()

    systemctl_names = []

    template = Template(template_string)
    # Assume we're running this script from the python root
    python_root = os.getcwd()
    for systemctl in systemctls:
        script_relative_path = systemctl.script_relative_path

        if systemctl.process_name_override is not None:
            process_name = systemctl.process_name_override
        else:
            process_name = pathlib.Path(script_relative_path).stem

        service_stem = service_prefix + '_' + process_name

        if systemctl.exec_before is not None:
            exec_start_pre = "ExecStartPre = {}".format(systemctl.exec_before)
        else:
            exec_start_pre = ""

        extra_environments_str = ''
        for env_var, env_value in systemctl.extra_environments.items():
            extra_environments_str += f'Environment={env_var}={env_value}\n'
        script_filename = os.path.join(relative_path_root, script_relative_path)
        service = template.substitute(
            name=process_name,
            log_name=service_stem,
            filename=script_filename,
            python_root=python_root,
            username=getpass.getuser(),
            exec_start_pre=exec_start_pre,
            python_executable=sys.executable,
            kill_mode=systemctl.kill_mode,
            extra_environments=extra_environments_str)
        service_filename = service_stem + '.service'
        service_path = f'/etc/systemd/system/{service_filename}'

        with tempfile.TemporaryDirectory() as tmpdirname:
            tmppath = os.path.join(tmpdirname, service_filename)
            with open(tmppath, 'w') as f:
                f.write(service)

            os.system(f'sudo mv -v {tmppath} {service_path}')

        print(f'Wrote {service_path} [name={process_name}, python root={python_root}.')
        systemctl_names.append(service_stem)

    print(f'Reloading...')
    os.system(f'sudo systemctl daemon-reload')
    print(f'Reloaded.')

    for systemctl_name in systemctl_names:
        print('Enabling {}'.format(systemctl_name))
        os.system(f'sudo systemctl enable {systemctl_name}')
        print('Starting {}'.format(systemctl_name))
        os.system(f'sudo systemctl restart {systemctl_name}')
    print('All done!')
