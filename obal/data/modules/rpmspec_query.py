#!/usr/bin/python
"""
Query a value from an RPM spec file

When dist is omitted, the dist macro is explicitly undefined.
"""

import subprocess

from ansible.module_utils.basic import AnsibleModule
try:
    from ansible.module_utils.obal import specfile_macro_lookup  # pylint:disable=import-error,no-name-in-module
except ImportError:
    from obal.data.module_utils.obal import specfile_macro_lookup  # pylint:disable=import-error,no-name-in-module


def query_spec(module):
    """Query the spec file and report rpmspec diagnostics through Ansible."""
    try:
        value, stderr = specfile_macro_lookup(
            module.params['spec_file'],
            module.params['query_format'],
            scl=module.params['scl'],
            dist=module.params['dist'],
            macros=module.params['macros'] or {},
        )
    except subprocess.CalledProcessError as error:
        module.fail_json(
            msg='Failed to query spec file',
            command=error.cmd,
            output=error.stdout,
            stderr=error.stderr,
            rc=error.returncode,
        )

    if 'incorrect format:' in stderr:
        module.fail_json(
            msg='Invalid query_format for spec file',
            command=[
                'rpmspec', '--query', '--queryformat', module.params['query_format'],
                '--srpm', module.params['spec_file'],
            ],
            output=value,
            stderr=stderr,
        )
    elif stderr:
        module.warn(stderr.strip())

    return value


def main():
    """
    Expand an rpmspec query format for a spec file
    """
    module = AnsibleModule(
        argument_spec=dict(
            spec_file=dict(type='path', required=True),
            query_format=dict(type='str', required=True),
            scl=dict(type='str', required=False),
            dist=dict(type='str', required=False),
            macros=dict(type='dict', required=False, default=None),
        ),
        supports_check_mode=True,
    )

    module.exit_json(changed=False, value=query_spec(module))


if __name__ == '__main__':
    main()
