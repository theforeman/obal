#!/usr/bin/python
"""
Verify packages against a tag in Koji
"""

import os
import subprocess

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.obal import get_specfile_name # pylint:disable=import-error,no-name-in-module
from ansible.module_utils.koji_wrapper import koji # pylint:disable=import-error,no-name-in-module

def main():
    """
    Verify packages against a tag in Koji
    """
    module = AnsibleModule(
        argument_spec=dict(
            packages=dict(type='dict', required=True),
            tag=dict(type='str', required=True),
            directory=dict(type='str', required=True),
            koji_executable=dict(type='str', require=False, default='koji')
        )
    )

    packages_for_tag = set()

    for (package, attributes) in module.params['packages'].items():
        tag = None

        if 'koji_tags' in attributes:
            for koji_tag in attributes['koji_tags']:
                if module.params['tag'] == koji_tag['name']:
                    tag = koji_tag

            if tag and 'package_base_dir' in attributes:
                specfile = os.path.join(attributes['package_base_dir'], package, "{}.spec".format(package))
                scl = tag.get('scl')
                name = get_specfile_name(os.path.join(module.params['directory'], specfile), scl)
                packages_for_tag.add(name)

    try:
        command = ['list-pkgs', '--quiet', '--tag', module.params['tag']]
        koji_output = koji(
            command,
            executable=module.params['koji_executable']
        )

        packages_in_koji = {item.split(' ', 1)[0] for item in koji_output.split("\n") if item}

    except subprocess.CalledProcessError as error:
        module.fail_json(changed=False, msg=error.output)

    missing_in_koji = packages_for_tag - packages_in_koji
    missing_in_git = packages_in_koji - packages_for_tag

    if missing_in_koji or missing_in_git:
        module.fail_json(
            changed=True,
            msg="Package differences found",
            missing_in_git=sorted(missing_in_git),
            missing_in_koji=sorted(missing_in_koji)
        )
    else:
        module.exit_json(changed=False)


if __name__ == '__main__':
    main()
