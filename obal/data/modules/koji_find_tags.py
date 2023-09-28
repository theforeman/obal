#!/usr/bin/python
"""
Find all defined Koji tags in inventory
"""

from ansible.module_utils.basic import AnsibleModule

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

    for attributes in packages.values():
        if 'koji_tags' in attributes:
            tags.update(tag['name'] for tag in attributes['koji_tags'])

    module.exit_json(changed=False, tags=sorted(tags))


if __name__ == '__main__':
    main()
