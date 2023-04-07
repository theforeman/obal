"""
A copr-cli wrapper and support functions for Copr
"""
from subprocess import check_output, CalledProcessError, STDOUT

class CoprCliCommandError(Exception):
    """Raised when copr-cli command fails"""
    def __init__(self, message, command):
        self.message = message
        self.command = command
        super(CoprCliCommandError, self).__init__(message) #pylint: disable-all

def copr_cli(command, executable=None, config_file=None):
    """
    Run a copr-cli command
    """
    if executable is None:
        executable = 'copr-cli'

    if config_file:
        command = ['--config', config_file] + command

    try:
        return check_output([executable] + command, universal_newlines=True, stderr=STDOUT)
    except CalledProcessError as error:
        raise CoprCliCommandError(error.output, error.cmd)

def full_name(user, project):
    """
    Returns a full Copr name: user/project
    """
    return "{}/{}".format(user, project)
