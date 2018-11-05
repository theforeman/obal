#!/usr/bin/env python2
# PYTHON_ARGCOMPLETE_OK

"""
Obal is a wrapper around Ansible playbooks. They are exposed as a command line application.
"""

from __future__ import print_function

import argparse
import errno
import glob
import json
import os
import sys
from collections import namedtuple
from functools import total_ordering

import yaml
from pkg_resources import resource_filename

try:
    import argcomplete
except ImportError:
    argcomplete = None


METADATA_FILENAME = 'metadata.obal.yaml'


# Need for PlaybookCLI to set the verbosity
display = None  # pylint: disable=C0103


def remove_prefix(text, prefix):
    """
    Remove the prefix from the text if present

    >>> remove_prefix('changelog_message', 'changelog_')
    'message'

    >>> remove_prefix('message', 'changelog')
    'message'
    """
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


Variable = namedtuple('Variable', ['name', 'parameter', 'help_text', 'action'])


@total_ordering
class Playbook(object):
    """
    An abstraction over an Ansible playbook
    """
    def __init__(self, path):
        self.path = path
        directory = os.path.dirname(path)
        self.name = os.path.basename(directory)
        self._metadata_path = os.path.join(directory, METADATA_FILENAME)
        self._metadata = None

    @property
    def metadata(self):
        """
        Read metadata about the playbook

        The metadata can contain a global help text as well as variables that should be exposed as
        command line parameters.

        This data is lazily loaded and cached.
        """
        if not self._metadata:
            try:
                with open(self._metadata_path) as obal_metadata:
                    data = yaml.load(obal_metadata)
            # Python 3 has FileNotFoundError, Python 2 doesn't
            except IOError as error:
                if error.errno != errno.ENOENT:
                    raise
                data = {}

            self._metadata = {
                'help': data.get('help'),
                'variables': sorted(self._parse_parameters(data.get('variables', {}))),
            }

        return self._metadata

    @property
    def takes_package_parameter(self):
        """
        Whether this playbook takes a package argument.

        This is determined by a hosts: packages inside the playbook
        """
        with open(self.path) as playbook_file:
            plays = yaml.load(playbook_file.read())

        return any('packages' in play['hosts'] for play in plays)

    @property
    def playbook_variables(self):
        """
        The playbook variables that should be exposed to the user

        This is extracted from the metadata.
        """
        return self.metadata['variables']

    @property
    def help_text(self):
        """
        The help text if available. This is the first line from the help in the metadata.
        """
        return self.metadata['help'].split('\n', 1)[0] if self.metadata['help'] else None

    @property
    def description(self):
        """
        The full help text if available. This is extracted from the metadata.
        """
        return self.metadata['help']

    def _parse_parameters(self, variables):
        """
        Parse parameters from the metadata.

        Automatically determines the parameter if not specified. This is done by looking at the
        variable and de-namespacing if it's namespaced. Also replaces underscores with dashes. This
        means that for the playbook changelog we expose changelog_message as --message but
        other_option as --other-option.
        """
        namespace = '{}_'.format(self.name)

        for name, options in variables.items():
            try:
                parameter = options['parameter']
            except KeyError:
                parameter = '--{}'.format(remove_prefix(name, namespace).replace('_', '-'))

            yield Variable(name, parameter, options.get('help'), options.get('action'))

    @property
    def __doc__(self):
        return self.description

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.path)

    def __eq__(self, other):
        if hasattr(other, 'path'):
            return self.path == other.path
        return NotImplemented

    def __lt__(self, other):
        if hasattr(other, 'name'):
            return self.name.__lt__(other.name)
        return NotImplemented


def find_playbooks(playbooks_path):
    """
    Find all playbooks in the given path.
    """
    paths = glob.glob(os.path.join(playbooks_path, '*', '*.yaml'))
    return sorted(Playbook(playbook_path) for playbook_path in paths if
                  os.path.basename(playbook_path) != METADATA_FILENAME)


def _get_data_path():
    """
    Return the data path. Houses playbooks and configs.
    """
    return resource_filename(__name__, 'data')


def get_playbooks_path():
    """
    Return the default playbooks path
    """
    return os.path.join(_get_data_path(), 'playbooks')


def get_ansible_config_path():
    """
    Return the default playbooks path
    """
    return os.path.join(_get_data_path(), 'ansible.cfg')


def find_packages(inventory_path):
    """
    Find all packages in the given inventory
    """
    package_choices = None
    if os.path.exists(inventory_path):
        from ansible.inventory.manager import InventoryManager
        from ansible.parsing.dataloader import DataLoader
        ansible_loader = DataLoader()
        ansible_inventory = InventoryManager(loader=ansible_loader,
                                             sources=inventory_path)
        package_choices = list(ansible_inventory.hosts.keys())
        package_choices.extend(ansible_inventory.groups.keys())
        package_choices.extend(['all'])
    return package_choices


def obal_argument_parser(playbooks=None, package_choices=None):
    """
    Construct an argument parser with the given actions and package choices.
    """
    if playbooks is None:
        playbooks = find_playbooks(get_playbooks_path())

    if package_choices is None:
        package_choices = []

    parser = argparse.ArgumentParser('obal')

    parser.obal_arguments = []

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-v", "--verbose",
                               action="count",
                               dest="verbose",
                               help="verbose output")

    advanced = parent_parser.add_argument_group('advanced arguments')
    advanced.add_argument('-e', '--extra-vars',
                          dest="extra_vars",
                          action="append",
                          default=[],
                          help="""set additional variables as key=value or
                          YAML/JSON, if filename prepend with @""")

    subparsers = parser.add_subparsers(dest='action', metavar='action',
                                       help="""which action to execute""")
    # Setting `required` outside of #add_subparser() is needed because
    # python2's #add_subparser() won't accept `required` as a field (even
    # though it's in the docs).
    subparsers.required = True

    for playbook in playbooks:
        subparser = subparsers.add_parser(playbook.name, parents=[parent_parser],
                                          help=playbook.help_text,
                                          description=playbook.description,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
        subparser.set_defaults(playbook=playbook)

        if playbook.takes_package_parameter:
            subparser.add_argument('package',
                                   metavar='package',
                                   choices=package_choices,
                                   nargs='+',
                                   help="the package to build")

        for variable in playbook.playbook_variables:
            subparser.add_argument(variable.parameter, help=variable.help_text, dest=variable.name,
                                   action=variable.action, default=argparse.SUPPRESS)
            parser.obal_arguments.append(variable.name)

    if argcomplete:
        argcomplete.autocomplete(parser)

    return parser


def generate_ansible_args(inventory_path, args, obal_arguments):
    """
    Generate the arguments to run ansible based on the parsed command line arguments
    """
    ansible_args = [args.playbook.path, '--inventory', inventory_path]
    if hasattr(args, 'package'):
        limit = ':'.join(args.package)
        ansible_args.extend(['--limit', limit])
    if args.verbose:
        ansible_args.append("-%s" % str("v" * args.verbose))
    for extra_var in args.extra_vars:
        ansible_args.extend(["-e", extra_var])

    variables = {arg: getattr(args, arg) for arg in obal_arguments if hasattr(args, arg)}
    if variables:
        ansible_args.extend(["-e", json.dumps(variables, sort_keys=True)])

    return ansible_args


def main(cliargs=None):  # pylint: disable=R0914
    """
    Main command
    """
    cfg_path = get_ansible_config_path()

    if os.path.exists(cfg_path):
        os.environ["ANSIBLE_CONFIG"] = cfg_path

    # this needs to be global, as otherwise PlaybookCLI fails
    # to set the verbosity correctly
    from ansible.utils.display import Display
    global display  # pylint: disable=C0103,W0603
    display = Display()

    inventory_path = os.path.join(os.getcwd(), 'package_manifest.yaml')

    package_choices = find_packages(inventory_path)

    parser = obal_argument_parser(package_choices=package_choices)

    args = parser.parse_args(cliargs)

    if args.playbook.takes_package_parameter and not os.path.exists(inventory_path):
        print("Could not find your package_manifest.yaml")
        exit(1)

    from ansible.cli.playbook import PlaybookCLI

    ansible_args = generate_ansible_args(inventory_path, args, parser.obal_arguments)
    ansible_playbook = (["ansible-playbook"] + ansible_args)

    if args.verbose:
        print(ansible_playbook)

    cli = PlaybookCLI(ansible_playbook)
    cli.parse()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
