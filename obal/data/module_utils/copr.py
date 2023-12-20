"""
A copr-cli wrapper and support functions for Copr
"""
import re
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

def project_exists(user, project, module, config_file=None):
    """
    Return true if a project already exists for a user
    """
    command = [
        'list',
        user
    ]

    try:
        project_list = copr_cli(command, config_file=config_file)
    except CoprCliCommandError as error:
        module.fail_json(msg='Copr project listing failed', command=' '.join(error.command), output=error.message)

    return re.search("Name: {}\n".format(project), project_list) is not None
