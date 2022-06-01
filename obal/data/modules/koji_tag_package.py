"""
Tag package build into Koji tag
"""

import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.koji_wrapper import koji, KojiCommandError # pylint:disable=import-error,no-name-in-module

def main():
    """
    Tag package build into Koji tag
    """
    module = AnsibleModule(
        argument_spec=dict(
            nvr=dict(type='str', required=True),
            tag=dict(type='str', required=True),
            koji_executable=dict(type='str', required=False)
        )
    )

    nvr = module.params['nvr']
    tag = module.params['tag']
    koji_executable = module.params['koji_executable']

    command = ['tag-build', tag, nvr]

    try:
        output = koji(command, koji_executable)
        task = re.findall(r'^Created task \s(\d+)', output, re.MULTILINE)

        module.exit_json(changed=True, output=output, task=task)
    except KojiCommandError as error:
        module.fail_json(changed=False, msg=error.message, command=error.command)


if __name__ == '__main__':
    main()
