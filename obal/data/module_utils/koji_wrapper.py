"""
A koji wrapper
"""
from subprocess import check_output, CalledProcessError, STDOUT

class KojiCommandError(Exception):
    """Raised when Koji command fails"""
    def __init__(self, message, command):
        self.message = message
        self.command = command
        super(KojiCommandError, self).__init__(message) #pylint: disable-all

def koji(command, executable=None):
    """
    Run a koji command
    """
    if executable is None:
        executable = 'koji'

    try:
        return check_output([executable] + command, universal_newlines=True, stderr=STDOUT)
    except CalledProcessError as error:
        raise KojiCommandError(error.output, error.cmd)


def package_whitelisted(executable, tag, package):
    """Check effective tag registration, excluding blocked packages."""
    try:
        output = koji(['list-pkgs', '--tag', tag, '--package', package, '--quiet'], executable)
    except KojiCommandError as error:
        if error.message.strip() == '(no matching packages)':
            return False
        raise
    return any(line.split() and line.split()[0] == package and '[BLOCKED]' not in line
               for line in output.splitlines())
