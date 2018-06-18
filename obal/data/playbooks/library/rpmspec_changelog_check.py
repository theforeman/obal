#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

from ansible.module_utils.basic import AnsibleModule

import os
import subprocess
import glob

def run_module():
    module_args = dict(
        directory=dict(type='str', required=True),
    )

    result = dict(
        changed=False,
        changelog_version_release='',
        specfile_version_release=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if module.check_mode:
        return result

    try:
        specfile = glob.glob(os.path.join(module.params['directory'], "*.spec"))[0]
    except IndexError:
        module.fail_json(msg="Could not find specfile", **result)

    try:
        cmd = ['rpm', '--query', '--changelog', '--specfile', specfile]
        result['changelog_version_release'] = subprocess.check_output(cmd).split("\n")[0].split(" ")[-1]

        cmd = ['rpmspec', '--query', '--queryformat', '%{version}-%{release}', '--undefine', 'dist', '--srpm', specfile]
        result['specfile_version_release'] = subprocess.check_output(cmd)
    except subprocess.CalledProcessError as err:
        module.fail_json(msg="An error occured while running [ {} ]".format(err.cmd), **result)

    if result['changelog_version_release'] != result['specfile_version_release']:
        module.fail_json(msg="changelog entry missing for {}".format(result['specfile_version_release']), **result)

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
