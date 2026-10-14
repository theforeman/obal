"""
A tito wrapper
"""
from subprocess import STDOUT, check_output


def tito(command, directory):
    """
    Run a tito command
    """
    return check_output(command, stderr=STDOUT, universal_newlines=True, cwd=directory)
