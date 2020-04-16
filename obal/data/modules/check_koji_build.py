"""
Check if build exists in Koji
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.koji_wrapper import koji, KojiCommandError # pylint:disable=import-error,no-name-in-module

def main():
    """
    Check if build exists in Koji
    """
    module = AnsibleModule(
        argument_spec=dict(
            tag=dict(type='str', required=True),
            nevr=dict(type='str', required=True),
            package=dict(type='str', required=True),
            koji_executable=dict(type='str', required=False)
        )
    )

    nevr = module.params['nevr']
    tag = module.params['tag']
    package = module.params['package']
    koji_executable = module.params['koji_executable']

    command = ['latest-build', '--quiet', tag, package]

    try:
        build = koji(command, koji_executable)
        build = build.split(' ')[0]

        module.exit_json(changed=False, tagged_version=build, exists=(nevr == build))
    except KojiCommandError as error:
        module.fail_json(changed=False, msg=error.message, command=error.command)


if __name__ == '__main__':
    main()
