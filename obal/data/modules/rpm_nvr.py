"""
Calculate name-version-release for an RPM package
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.obal import get_specfile_nvr, get_specfile_name # pylint:disable=import-error,no-name-in-module


def main():
    """
    Calculate name-version-release for a specfile
    """
    module = AnsibleModule(
        argument_spec=dict(
            spec_file=dict(type='str', required=True),
            scl=dict(type='str', required=False),
            dist=dict(type='str', required=False),
            macros=dict(type='dict', required=False, default={})
        )
    )

    nvr = get_specfile_nvr(
        module.params['spec_file'],
        scl=module.params['scl'],
        dist=module.params['dist'],
        macros=module.params['macros']
    )

    name = get_specfile_name(
        module.params['spec_file'],
        scl=module.params['scl']
    )

    module.exit_json(changed=False, nvr=nvr, name=name)


if __name__ == '__main__':
    main()
