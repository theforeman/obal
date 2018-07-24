#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

from ansible.module_utils.basic import AnsibleModule

import os
from six.moves import configparser

def run_module():
    module_args = dict(
        package=dict(type="str", required=True),
        tito_props_path=dict(type="str", required=True),
    )

    result = dict(
        changed=False,
        disttag=None,
        scl=None
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if module.check_mode:
        return result

    config = configparser.ConfigParser()
    config.read(module.params['tito_props_path'])

    packaging_sections = [section for section in config.sections() if config.has_option(section, 'whitelist')]

    section = []
    for psection in packaging_sections:
        if module.params['package'] in config.get(psection, 'whitelist'):
            section.append(psection)

    if len(section) > 1:
        module.fail_json(msg="package found in more than one whitelst", **result)

    section = section[0]
    result['disttag'] = config.get(section, 'disttag')
    if config.has_option(section, 'scl'):
        result['scl'] = config.get(section, 'scl')

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
