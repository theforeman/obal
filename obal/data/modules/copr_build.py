"""
Release a package to Copr
"""

import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.copr import copr_cli, CoprCliCommandError, full_name # pylint:disable=import-error,no-name-in-module


def main():
    """
	Release a package to Copr
    """
    module = AnsibleModule(
        argument_spec=dict(
            user=dict(type='str', required=True),
            project=dict(type='str', required=True),
            srpm=dict(type='path', required=True),
            wait=dict(type='bool', required=False, default=False),
            chroots=dict(type='list', required=False),
            config_file=dict(type='str', required=False),
        )
    )

    user = module.params['user']
    project = module.params['project']
    srpm = module.params['srpm']
    wait = module.params['wait']
    chroots = module.params['chroots']
    config_file = module.params['config_file']

    command = [
        'build',
        full_name(user, project),
        srpm
    ]

    if not wait:
        command.append('--nowait')

    if chroots:
        for chroot in chroots:
            command.extend(['--chroot', chroot])

    try:
        output = copr_cli(command, config_file=config_file)
    except CoprCliCommandError as error:
        module.fail_json(msg='Copr build failed', command=error.command, output=error.message,
                         repo_name=full_name(user, project), srpm=srpm)

    build_urls = re.findall(r'^Build was added to.+:\n^\s+(.+)\s*', output, re.MULTILINE)
    builds = re.findall(r'^Created builds:\s(\d+)', output, re.MULTILINE)

    module.exit_json(changed=True, output=output, builds=builds, build_urls=build_urls)


if __name__ == '__main__':
    main()
