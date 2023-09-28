#!/usr/bin/python
"""
Retrieve a particular build for a package in Copr
"""

import json
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.copr import copr_cli, CoprCliCommandError, full_name # pylint:disable=import-error,no-name-in-module


def main():
    """
    Retrieve a particular build for a package in Copr
    """
    module = AnsibleModule(
        argument_spec=dict(
            user=dict(type='str', required=True),
            project=dict(type='str', required=True),
            nevr=dict(type='str', required=True),
            package=dict(type='str', required=True),
            config_file=dict(type='str', required=False),
        )
    )

    user = module.params['user']
    project = module.params['project']
    nevr = module.params['nevr']
    package = module.params['package']
    config_file = module.params['config_file']

    command = [
        'get-package',
        full_name(user, project),
        '--name',
        package,
        '--with-all-builds'
    ]

    try:
        package_info = json.loads(copr_cli(command, config_file=config_file))
    except CoprCliCommandError as error:
        if "Error: No package with name {} in copr {}".format(package, project) in error.message:
            module.exit_json(exists=False)
        else:
            module.fail_json(msg='Retrieval of package from Copr failed', command=command, output=error.message,
                             repo_name=full_name(user, project), package=package)

    successful_builds = (build for build in package_info['builds'] if build['state'] == 'succeeded')
    successful_nevrs = ("{}-{}".format(package, build['source_package']['version']) for build in successful_builds)
    exists = nevr in successful_nevrs

    module.exit_json(info=package_info, exists=exists)


if __name__ == '__main__':
    main()
