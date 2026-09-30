#!/usr/bin/python
"""Release packages through rhpkg, reusing and tagging existing Koji builds."""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.rhpkg import RhpkgRelease, ReleaseError, inventory_tags  # pylint:disable=import-error,no-name-in-module


def main():
    """Submit builds and reconcile output tags without invoking Tito."""
    module = AnsibleModule(
        argument_spec=dict(
            directory=dict(type='path', required=True),
            spec_file=dict(type='path', required=True),
            targets=dict(type='list', elements='dict', required=True),
            koji_tags=dict(type='list', elements='dict', default=[]),
            koji_executable=dict(type='str', default='brew'),
            rhpkg_executable=dict(type='str', default='rhpkg'),
            receipt=dict(type='path', required=True),
            output_directory=dict(type='path', required=True),
            scratch=dict(type='bool', default=False),
            wait=dict(type='bool', default=True),
            waitrepo=dict(type='bool', default=False),
            tag_check=dict(type='bool', default=True),
            download_logs=dict(type='bool', default=False),
            download_rpms=dict(type='bool', default=False),
        ),
        supports_check_mode=True,
    )
    release = None
    try:
        package = module.params['directory'].rstrip('/').split('/')[-1]
        inventory_tags(dict(build_package_releaser='rhpkg', rhpkg_targets=module.params['targets'],
                            koji_tags=module.params['koji_tags']), package)
        release = RhpkgRelease(dict(module.params, check_mode=module.check_mode))
        result = release.execute()
    except (ReleaseError, OSError, ValueError) as error:
        module.fail_json(msg=str(error), changed=release.changed if release else False,
                         results=release.results if release else [])
    if result['errors']:
        module.fail_json(msg='; '.join(result['errors']), **result)
    module.exit_json(**result)


if __name__ == '__main__':
    main()
