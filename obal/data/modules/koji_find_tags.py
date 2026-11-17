#!/usr/bin/python
"""
Find all defined Koji tags in inventory
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.rhpkg import inventory_tags, ReleaseError  # pylint:disable=import-error,no-name-in-module

def main():
    """
    Find all defined Koji tags in inventory
    """
    module = AnsibleModule(
        argument_spec=dict(
            packages=dict(type='dict', required=True)
        )
    )

    packages = module.params['packages']

    tags = set()

    try:
        for package, attributes in packages.items():
            tags.update(tag['name'] for tag in inventory_tags(attributes, package))
    except ReleaseError as error:
        module.fail_json(msg=str(error))

    module.exit_json(changed=False, tags=sorted(tags))


if __name__ == '__main__':
    main()
