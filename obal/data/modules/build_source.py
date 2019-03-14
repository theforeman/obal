"""
Build a source package
"""

import os
from subprocess import CalledProcessError, check_output
from contextlib import contextmanager

from ansible.module_utils.basic import AnsibleModule


@contextmanager
def chdir(directory):
    """
    Change the directory in a context manager. Automatically switches back even if an exception
    occurs.
    """
    old = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(old)


def main():
    """
    Build a source package
    """
    module = AnsibleModule(
        argument_spec=dict(
            directory=dict(required=True),
        )
    )

    directory = module.params['directory']
    path = None

    with chdir(directory):
        if os.path.exists(os.path.join(directory, 'Rakefile.dist')):
            try:
                path = check_output(['rake', '-f', 'Rakefile.dist', 'pkg:generate_source'],
                                    universal_newlines=True).rstrip()
            except CalledProcessError as error:
                module.fail_json(msg='Failed to build using Rakefile.dist',
                                 stdout=error.stdout, stderr=error.stderr)

            if not os.path.isabs(path):
                path = os.path.join(directory, path)
        else:
            module.fail_json(msg='Unsupported package directory')


    module.exit_json(changed=path is not None, path=path)


if __name__ == '__main__':
    main()
