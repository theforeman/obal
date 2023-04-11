"""
Create a Project in Copr
"""

import re
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.copr import copr_cli, CoprCliCommandError, full_name # pylint:disable=import-error,no-name-in-module


def project_exists(user, project, module):
    """
    Return true if a project already exists for a user
    """
    command = [
        'list',
        user
    ]

    try:
        project_list = copr_cli(command)
    except CoprCliCommandError as error:
        module.fail_json(msg='Copr project listing failed', command=' '.join(error.command), output=error.message)

    return re.search("Name: {}\n".format(project), project_list) is not None

def main():
    """
    Create a Project in Copr
    """
    module = AnsibleModule(
        argument_spec=dict(
            user=dict(type='str', required=True),
            project=dict(type='str', required=True),
            chroots=dict(type='list', required=True),
            description=dict(type='str', required=False),
            unlisted_on_homepage=dict(type='bool', required=False, default=False),
            delete_after_days=dict(type='str', required=False),
        )
    )

    user = module.params['user']
    project = module.params['project']
    chroots = module.params['chroots']
    description = module.params['description']
    unlisted_on_homepage = module.params['unlisted_on_homepage']
    delete_after_days = module.params['delete_after_days']

    if not description:
        description = project

    if project_exists(user, project, module):
        command = ['modify']
    else:
        command = ['create']

    command.extend([
        full_name(user, project),
        '--description',
        description
    ])

    for chroot in chroots:
        command.extend(['--chroot', chroot])

    if unlisted_on_homepage:
        command.extend(['--unlisted-on-hp', 'on'])

    if delete_after_days:
        command.extend(['--delete-after-days', delete_after_days])

    try:
        output = copr_cli(command)
    except CoprCliCommandError as error:
        module.fail_json(msg='Copr project creation failed', command=' '.join(error.command), output=error.message)

    module.exit_json(changed=True, output=output)


if __name__ == '__main__':
    main()
