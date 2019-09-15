"""
Release a package using tito
"""

import re
from subprocess import CalledProcessError

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tito_wrapper import tito  # pylint:disable=import-error,no-name-in-module


def main():
    """
    Release a package using tito
    """
    module = AnsibleModule(
        argument_spec=dict(
            directory=dict(type='path', required=True),
            arguments=dict(type='list', required=False),
            scratch=dict(type='bool', required=False, default=False),
            test=dict(type='bool', required=False, default=False),
            releasers=dict(type='list', required=True),
            releaser_arguments=dict(type='list', required=False),
        )
    )

    command = ['tito', 'release', '--yes']

    for param in ('scratch', 'test'):
        if module.params[param]:
            command.append('--' + param)

    command += module.params['releasers']

    if module.params['releaser_arguments']:
        for argument in module.params['releaser_arguments']:
            command += ['--arg', argument]

    if module.params['arguments']:
        command += module.params['arguments']

    directory = module.params['directory']

    try:
        output = tito(command, directory)
    except CalledProcessError as error:
        module.fail_json(msg='Failed to tito release', command=error.cmd, directory=directory,
                         output=error.output, code=error.returncode)

    tasks = re.findall(r'^Created task:\s(\d+)', output, re.MULTILINE)
    task_urls = re.findall(r'^Task info:\s(.+)', output, re.MULTILINE)
    builds = re.findall(r'^Created builds:\s(\d+)', output, re.MULTILINE)

    module.exit_json(changed=True, output=output, tasks=tasks, task_urls=task_urls, builds=builds)


if __name__ == '__main__':
    main()
