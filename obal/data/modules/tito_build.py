"""
Release a package using tito
"""

import re
from subprocess import CalledProcessError

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tito_wrapper import tito  # pylint:disable=import-error,no-name-in-module


def main():
    """
    Build a package using tito
    """
    module = AnsibleModule(
        argument_spec=dict(
            directory=dict(type='path', required=True),
            arguments=dict(type='list', required=False),
            build_arguments=dict(type='list', required=False),
            srpm=dict(type='bool', required=False, default=False),
            offline=dict(type='bool', required=False, default=False),
            dist=dict(type='str', required=False),
            scl=dict(rtype='str', equired=False),
            output=dict(type='path', required=False),
            builder=dict(type='str', required=False),
        )
    )

    command = ['tito', 'build']

    for param in ('srpm', 'offline'):
        if module.params[param]:
            command.append('--' + param)

    for param in ('dist', 'scl', 'output', 'builder'):
        value = module.params[param]
        if value:
            command += ['--' + param, value]

    if module.params['build_arguments']:
        for argument in module.params['build_arguments']:
            command += ['--arg', argument]

    if module.params['arguments']:
        command += module.params['arguments']

    directory = module.params['directory']

    try:
        output = tito(command, directory)
    except CalledProcessError as error:
        module.fail_json(msg='Failed to tito build', command=error.cmd, output=error.output,
                         directory=directory, code=error.returncode)

    match = re.search(r'^Wrote: (?P<path>.+)', output, re.MULTILINE)
    path = match.group('path') if match else None

    module.exit_json(changed=True, path=path, output=output)


if __name__ == '__main__':
    main()
