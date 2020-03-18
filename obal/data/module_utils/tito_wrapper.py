"""
A tito wrapper
"""
from subprocess import STDOUT, check_output

from ansible.module_utils.obal import chdir # pylint:disable=import-error,no-name-in-module


def tito(command, directory):
    """
    Run a tito command
    """
    with chdir(directory):
        return check_output(command, stderr=STDOUT, universal_newlines=True)
