#!/usr/bin/python
"""
Manage a chroot in a Copr project
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.copr import copr_cli, CoprCliCommandError, full_name # pylint:disable=import-error,no-name-in-module


def main():
    """
    Manage a chroot in a Copr project
    """
    module = AnsibleModule(
        argument_spec=dict(
            user=dict(type='str', required=True),
            project=dict(type='str', required=True),
            chroot=dict(type='str', required=True),
            external_repos=dict(type='list', required=False),
            buildroot_packages=dict(type='list', required=False),
            modules=dict(type='list', required=False),
            config_file=dict(type='str', required=False),
            comps_file=dict(type='str', required=False),
        )
    )

    user = module.params['user']
    project = module.params['project']
    chroot = module.params['chroot']
    external_repos = module.params['external_repos']
    buildroot_packages = module.params['buildroot_packages']
    modules = module.params['modules']
    config_file = module.params['config_file']
    comps_file = module.params['comps_file']

    command = [
        'edit-chroot',
        "{}/{}".format(full_name(user, project), chroot)
    ]

    if external_repos:
        command.extend(['--repos', ' '.join(external_repos)])

    if buildroot_packages:
        command.extend(['--packages', ' '.join(buildroot_packages)])

    if modules:
        command.extend(['--modules', ','.join(modules)])

    if comps_file:
        command.extend(['--upload-comps', comps_file])

    try:
        output = copr_cli(command, config_file=config_file)
    except CoprCliCommandError as error:
        module.fail_json(msg='Copr chroot edit failed', command=' '.join(error.command), output=error.message)

    module.exit_json(changed=True, output=output)


if __name__ == '__main__':
    main()
