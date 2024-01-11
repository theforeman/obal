#!/usr/bin/python
"""
Release a package to Copr
"""

import re
import json

from subprocess import CalledProcessError
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.copr import copr_cli, CoprCliCommandError, full_name # pylint:disable=import-error,no-name-in-module
from ansible.module_utils.obal import get_srpm_name, get_srpm_nevr # pylint:disable=import-error,no-name-in-module


def get_package_info(module, user, project, package, config_file=None):
    """
    Fetch package info from Copr
    """
    command = [
        'get-package',
        full_name(user, project),
        '--name',
        package,
        '--with-all-builds'
    ]

    try:
        info = json.loads(copr_cli(command, config_file=config_file))
    except CoprCliCommandError as error:
        if "Error: No package with name {} in copr {}".format(package, project) in error.message:
            info = {}
        else:
            module.fail_json(msg='Retrieval of package from Copr failed', command=command, output=error.message,
                             repo_name=full_name(user, project), package=package)

    return info

def build_exists(nevr, package_info, chroot=None):
    """
    Determine if build exists in Copr for a given NEVR
    """
    exists = False

    if 'builds' in package_info:
        chroots = [
            build for build in package_info['builds']
            if chroot in build['chroots']
        ]
        successful_builds = [
            build for build in chroots
            if build['state'] in ['succeeded', 'forked']
        ]
        successful_nevrs = [
            "{}-{}".format(build['source_package']['name'], build['source_package']['version'])
            for build in successful_builds
        ]

        exists = nevr in set(successful_nevrs)

    return exists

def main():
    """
    Release a package to Copr
    """
    module = AnsibleModule(
        argument_spec=dict(
            user=dict(type='str', required=True),
            project=dict(type='str', required=True),
            srpm=dict(type='path', required=True),
            wait=dict(type='bool', required=False, default=False),
            chroot=dict(type='str', required=False),
            config_file=dict(type='str', required=False),
            force=dict(type='bool', required=False, default=False)
        )
    )

    user = module.params['user']
    project = module.params['project']
    srpm = module.params['srpm']
    wait = module.params['wait']
    chroot = module.params['chroot']
    config_file = module.params['config_file']
    force = module.params['force']

    try:
        package_name = get_srpm_name(srpm)
        nevr = get_srpm_nevr(srpm)
    except CalledProcessError as error:
        module.fail_json(msg=error.output, command=error.cmd, output=error.output)

    package_info = get_package_info(module, user, project, package_name, config_file)

    if force or not build_exists(nevr, package_info, chroot):
        command = [
            'build',
            full_name(user, project),
            srpm,
            '--chroot',
            chroot
        ]

        if not wait:
            command.append('--nowait')

        try:
            output = copr_cli(command, config_file=config_file)
        except CoprCliCommandError as error:
            module.fail_json(msg='Copr build failed', command=error.command, output=error.message,
                             repo_name=full_name(user, project), srpm=srpm)

        build_urls = re.findall(r'^Build was added to.+:\n^\s+(.+)\s*', output, re.MULTILINE)
        builds = re.findall(r'^Created builds:\s(\d+)', output, re.MULTILINE)

        module.exit_json(changed=True, output=output, builds=builds, build_urls=build_urls)
    else:
        module.exit_json(changed=False)


if __name__ == '__main__':
    main()
