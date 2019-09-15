"""
A tito wrapper
"""
import os
from contextlib import contextmanager
from subprocess import STDOUT, check_output


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


def tito(command, directory):
    """
    Run a tito command
    """
    with chdir(directory):
        return check_output(command, stderr=STDOUT, universal_newlines=True)
