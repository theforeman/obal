#!/usr/bin/python
"""Check Koji package registration for explicit tags or legacy releaser configuration."""

import configparser

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.obal import specfile_macro_lookup  # pylint:disable=import-error,no-name-in-module
from ansible.module_utils.koji_wrapper import package_whitelisted, KojiCommandError  # pylint:disable=import-error,no-name-in-module


def run_module():
    """Fail before tagging if the package is absent or blocked in any destination."""
    module = AnsibleModule(
        argument_spec=dict(
            releasers_conf=dict(type='path'),
            spec_file_path=dict(type='path'),
            releasers=dict(type='list', elements='str', default=[]),
            build_command=dict(type='str', required=True),
            package=dict(type='str'),
            tags=dict(type='list', elements='str'),
            scl=dict(type='str'),
            dist=dict(type='str'),
            macros=dict(type='dict'),
        ),
        required_one_of=[['package', 'spec_file_path'], ['tags', 'releasers_conf']],
        mutually_exclusive=[['tags', 'releasers_conf']],
        supports_check_mode=True,
    )
    result = dict(changed=False, branches=[], autobuild_tags=[], whitelist_status={})
    tags = module.params['tags'] or []
    if module.params['releasers_conf']:
        config = configparser.ConfigParser(allow_no_value=True)
        try:
            with open(module.params['releasers_conf']) as stream:
                config.read_file(stream)
            for releaser in module.params['releasers']:
                for field in ('branches', 'autobuild_tags'):
                    if config.has_option(releaser, field):
                        result[field].extend((config.get(releaser, field) or '').split())
        except (OSError, configparser.Error) as error:
            module.fail_json(msg=str(error), **result)
        tags = result['branches'] + result['autobuild_tags']
    if not tags:
        module.fail_json(msg='No destination tags configured for package registration checks', **result)

    package = module.params['package']
    if not package:
        package, _ = specfile_macro_lookup(module.params['spec_file_path'], '%{name}',
                                           scl=module.params['scl'], dist=module.params['dist'],
                                           macros=module.params['macros'])
    try:
        for tag in dict.fromkeys(tags):
            result['whitelist_status'][tag] = package_whitelisted(module.params['build_command'], tag, package)
    except KojiCommandError as error:
        module.fail_json(msg=error.message, command=error.command, **result)
    missing = [tag for tag, registered in result['whitelist_status'].items() if not registered]
    if missing:
        module.fail_json(msg='Package {} is not registered or is blocked in tags: {}'.format(
            package, ', '.join(missing)), **result)
    module.exit_json(**result)


if __name__ == '__main__':
    run_module()
