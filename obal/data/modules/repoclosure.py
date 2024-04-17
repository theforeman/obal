#!/usr/bin/python
"""
Run repoclosure on a set of repositories
"""

from subprocess import check_output, CalledProcessError, STDOUT
from ansible.module_utils.basic import AnsibleModule


def main():
    """
    Run repoclosure on a set of repositories
    """
    module = AnsibleModule(
        argument_spec=dict(
            config=dict(type='str', required=True),
            check=dict(type='list', required=True),
            additional_repos=dict(type='list', required=False, default=[]),
            lookaside=dict(type='list', required=False, default=[]),
            arch=dict(type='list', required=False, default=['noarch', 'x86_64']),
        )
    )

    config = module.params['config']
    check = module.params['check']
    additional_repos = module.params['additional_repos']
    lookaside = module.params['lookaside']

    command = [
        'dnf',
        'repoclosure',
        '--refresh',
        '--newest',
        '--config',
        config
    ]

    for arch in module.params['arch']:
        command.extend(['--arch', arch])

    for name in check:
        command.extend(['--check', name])
        command.extend(['--repo', name])

    for repo in additional_repos:
        command.extend(['--repofrompath', '{},{}'.format(repo['name'], repo['url'])])

    for repo in lookaside:
        command.extend(['--repo', repo])

    try:
        output = check_output(command, universal_newlines=True, stderr=STDOUT)
    except CalledProcessError as error:
        module.fail_json(msg='Repoclosure failed', command=' '.join(command), output=error.output)

    module.exit_json(changed=False, output=output)


if __name__ == '__main__':
    main()
