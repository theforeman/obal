"""
Release a package to koji
"""

import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.koji_wrapper import koji, KojiCommandError # pylint:disable=import-error,no-name-in-module
from ansible.module_utils.obal import get_whitelist_status  # pylint:disable=import-error,no-name-in-module


def main():
    """
    Build a package in koji
    """
    module = AnsibleModule(
        argument_spec=dict(
            srpm=dict(type='path', required=True),
            scratch=dict(type='bool', required=False, default=False),
            tag=dict(type='str', required=True),
            nevr=dict(type='str', required=True),
            package=dict(type='str', required=True),
            tag_check=dict(type='bool', required=False, default=True),
            koji_executable=dict(type='str', required=False)
        )
    )

    tag = module.params['tag']
    scratch = module.params['scratch']
    srpm = module.params['srpm']
    nevr = module.params['nevr']
    package = module.params['package']
    koji_executable = module.params['koji_executable']

    if module.params['tag_check']:
        if not get_whitelist_status(koji_executable, tag, package):
            module.fail_json(msg="Package {} has not been added to tag {}".format(package, tag))

    if not scratch:
        try:
            command = ['latest-build', '--quiet', tag, package]
            koji_output = koji(command, koji_executable)
            build = koji_output.split(' ')[0].strip()

            if build == nevr:
                module.exit_json(changed=False, build=build)
        except KojiCommandError as error:
            module.fail_json(changed=False, msg=error, command=command)

    command = ['build', tag, srpm]

    if scratch:
        command.append('--scratch')

    try:
        output = koji(command, koji_executable)
    except KojiCommandError as error:
        module.fail_json(msg='Failed to koji build', command=error.cmd, output=error.output,
                         tag=tag, scratch=scratch, srpm=srpm, code=error.returncode)

    tasks = re.findall(r'^Created task:\s(\d+)', output, re.MULTILINE)
    task_urls = re.findall(r'^Task info:\s(.+)', output, re.MULTILINE)
    builds = re.findall(r'^Created builds:\s(\d+)', output, re.MULTILINE)

    module.exit_json(changed=True, output=output, tasks=tasks, task_urls=task_urls, builds=builds)


if __name__ == '__main__':
    main()
