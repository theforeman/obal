#!/usr/bin/python
"""
Verify packages against a tag in Koji
"""

import os
import subprocess

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.obal import specfile_macro_lookup # pylint:disable=import-error,no-name-in-module
from ansible.module_utils.koji_wrapper import koji # pylint:disable=import-error,no-name-in-module
from ansible.module_utils.rhpkg import inventory_tags, uses_rhpkg, ReleaseError  # pylint:disable=import-error,no-name-in-module

def main():
    """
    Verify packages against a tag in Koji
    """
    module = AnsibleModule(
        argument_spec=dict(
            packages=dict(type='dict', required=True),
            tag=dict(type='str', required=True),
            directory=dict(type='str', required=True),
            koji_executable=dict(type='str', required=False)
        )
    )

    packages_for_tag = set()
    executables = set()

    for (package, attributes) in module.params['packages'].items():
        tag = None

        try:
            tags = inventory_tags(attributes, package)
        except ReleaseError as error:
            module.fail_json(msg=str(error))

        if tags:
            for koji_tag in tags:
                if module.params['tag'] == koji_tag['name']:
                    tag = koji_tag

            if tag and ('package_base_dir' in attributes or uses_rhpkg(attributes)):
                specfile = os.path.join(attributes.get('package_base_dir', 'packages'), package,
                                        "{}.spec".format(package))
                directory = attributes.get('inventory_dir', module.params['directory'])
                name, _ = specfile_macro_lookup(os.path.join(directory, specfile), '%{name}',
                                                scl=tag.get('scl'), dist=tag.get('dist'), macros=tag.get('macros'))
                packages_for_tag.add(name)
                default_command = 'brew' if uses_rhpkg(attributes) else 'koji'
                executables.add(attributes.get('build_package_koji_command',
                                                attributes.get('koji_executable', default_command)))

    executable = module.params['koji_executable']
    if not executable:
        if len(executables) > 1:
            module.fail_json(msg='Packages for this tag select different Koji executables')
        executable = next(iter(executables), 'koji')

    try:
        command = ['list-pkgs', '--quiet', '--tag', module.params['tag']]
        koji_output = koji(
            command,
            executable=executable
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
