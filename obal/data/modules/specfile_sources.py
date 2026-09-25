#!/usr/bin/python
"""
List sources and patches from an RPM spec file
"""

import subprocess

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.obal import get_specfile_sources  # pylint:disable=import-error,no-name-in-module


def main():
    """
    Return the sources and patches declared by an RPM spec file
    """
    module = AnsibleModule(
        argument_spec=dict(
            spec_file=dict(type='path', required=True),
        ),
        supports_check_mode=True,
    )

    try:
        sources = get_specfile_sources(module.params['spec_file'])
    except subprocess.CalledProcessError as error:
        module.fail_json(
            msg='Failed to list sources from spec file',
            command=error.cmd,
            output=error.output,
        )

    module.exit_json(changed=False, sources=sources)


if __name__ == '__main__':
    main()
