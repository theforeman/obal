#!/usr/bin/python
"""
Check if build exists in Koji
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.koji_wrapper import koji, KojiCommandError # pylint:disable=import-error,no-name-in-module
from ansible.module_utils.rhpkg import build_info, ReleaseError # pylint:disable=import-error,no-name-in-module

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

    try:
        info = build_info(koji_executable or 'koji', nvr)
    except ReleaseError as error:
        module.fail_json(msg=str(error), changed=False)
    exists = info['state'] == 'COMPLETE'
    result = dict(changed=False, exists=exists, state=info['state'], task=info['task'])

    if tag:
        exists_for_tag = exists and tag in info['tags']

        if not exists_for_tag:
            command = ['latest-build', '--quiet', tag, package]

            try:
                build = koji(command, koji_executable)
            except KojiCommandError as error:
                module.fail_json(changed=False, msg=error.message, command=error.command)

            build = build.split(' ')[0]
            module.exit_json(tagged_version=build, exists_for_tag=False, **result)
        else:
            module.exit_json(tagged_version=nvr, exists_for_tag=True, **result)
    else:
        module.exit_json(**result)

if __name__ == '__main__':
    main()
