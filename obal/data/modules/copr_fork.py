#!/usr/bin/python
"""
Fork a Copr project
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.copr import copr_cli, CoprCliCommandError, full_name, project_exists # pylint:disable=import-error,no-name-in-module


def main():
    """
    Fork a Copr project
    """
    module = AnsibleModule(
        argument_spec=dict(
            src_user=dict(type='str', required=True),
            src_project=dict(type='str', required=True),
            dest_user=dict(type='str', required=True),
            dest_project=dict(type='str', required=True),
            delete_after_days=dict(type='str', required=False, default=None),
            config_file=dict(type='str', required=False),
        )
    )

    src_user = module.params['src_user']
    src_project = module.params['src_project']
    dest_user = module.params['dest_user']
    dest_project = module.params['dest_project']
    delete_after_days = module.params['delete_after_days']
    config_file = module.params['config_file']

    if project_exists(dest_user, dest_project, module, config_file=config_file):
        module.exit_json(changed=False)

    command = [
        'fork',
        full_name(src_user, src_project),
        full_name(dest_user, dest_project)
    ]

    try:
        fork_output = copr_cli(command, config_file=config_file)
    except CoprCliCommandError as error:
        module.fail_json(msg='Copr project forking failed', command=' '.join(error.command), output=error.message)

    if delete_after_days:
        modify_command = [
            'modify',
            full_name(dest_user, dest_project),
            '--delete-after-days',
            delete_after_days
        ]

        try:
            copr_cli(modify_command, config_file=config_file)
        except CoprCliCommandError as error:
            module.fail_json(msg='Copr project forking failed', command=' '.join(error.command), output=error.message)

    module.exit_json(changed=True, output=fork_output)


if __name__ == '__main__':
    main()
