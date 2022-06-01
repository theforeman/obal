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
            tag=dict(type='str', required=False),
            nvr=dict(type='str', required=True),
            package=dict(type='str', required=True),
            koji_executable=dict(type='str', required=False)
        )
    )

    nvr = module.params['nvr']
    tag = module.params['tag']
    package = module.params['package']
    koji_executable = module.params['koji_executable']

    command = ['buildinfo', nvr]
    try:
        output = koji(command, koji_executable)
        exists = "BUILD: %s" % (nvr) in output
    except KojiCommandError:
        output = None
        exists = False

    if tag:
        exists_for_tag = False

        if output is not None:
            for line in output.split("\n"):
                if line.startswith("Tags:"):
                    tags = line.split()[1:]
                    exists_for_tag = tag in tags

        if not exists_for_tag:
            command = ['latest-build', '--quiet', tag, package]

            try:
                build = koji(command, koji_executable)
            except KojiCommandError as error:
                module.fail_json(changed=False, msg=error.message, command=error.command)

            build = build.split(' ')[0]
            module.exit_json(changed=False, exists=exists, tagged_version=build, exists_for_tag=False)
        else:
            module.exit_json(changed=False, exists=exists, tagged_version=nvr, exists_for_tag=True)
    else:
        module.exit_json(changed=False, exists=exists)

if __name__ == '__main__':
    main()
