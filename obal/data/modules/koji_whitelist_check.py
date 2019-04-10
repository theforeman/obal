# pylint: disable=C0111,C0301,R1710

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import os

from ansible.module_utils.basic import AnsibleModule  # pylint: disable=C0413
from ansible.module_utils.obal import get_specfile_name, get_whitelist_status  # pylint:disable=import-error,no-name-in-module

ANSIBLE_METADATA = {
    'metadata_version': '1.2',
    'status': ['preview'],
    'supported_by': 'community'
}


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            releasers_conf=dict(type='str', required=True),
            spec_file_path=dict(type='str', required=True),
            releasers=dict(type='list', required=True),
            build_command=dict(type='str', required=True),
        )
    )

    result = dict(
        changed=False,
        branches=[],
        autobuild_tags=[],
        whitelist_status=dict(),
    )

    releasers_config = module.params['releasers_conf']

    # fail if we can't find a releasers.conf
    if not os.path.isfile(releasers_config):
        module.fail_json(msg="Config file [ {} ] could not be found.".format(releasers_config), **result)

    config = configparser.ConfigParser(allow_no_value=True)
    config.read(releasers_config)

    package_name = get_specfile_name(module.params['spec_file_path'])

    # get branches and tags
    for releaser in module.params['releasers']:
        if config.has_option(releaser, 'branches'):
            result['branches'] = config.get(releaser, 'branches').split(' ')
        if config.has_option(releaser, 'autobuild_tags'):
            result['autobuild_tags'] = config.get(releaser, 'autobuild_tags').split(' ')

    # fail if we don't find any branches or autobuild_tags
    if not result['branches'] and not result['autobuild_tags']:
        module.fail_json(msg="No branches or autobuild_tags were found mapped to {}.".format(module.params['releasers']), **result)

    # check whitelist status
    for tag in result['branches'] + result['autobuild_tags']:
        status = get_whitelist_status(module.params['build_command'], tag, package_name)
        result['whitelist_status'][tag] = status

    if not all(result['whitelist_status'].values()):
        module.fail_json(msg="Package has not been whitelisted for given branches and autobuild_tags", **result)

    module.exit_json(**result)


if __name__ == '__main__':
    run_module()
