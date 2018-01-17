#!/usr/bin/env python2
# PYTHON_ARGCOMPLETE_OK

from __future__ import print_function

import argparse
import os

from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from pkg_resources import resource_filename

try:
    import argcomplete
except ImportError:
    argcomplete = None

_PLAYBOOKS = {
    'add': 'add_package.yml',
    'check': 'check_package.yml',
    'release': 'release_package.yml',
    'scratch': 'scratch_build.yml',
    'update': 'update_package.yml'
}


def find_packages(inventory_path):
    package_choices = None
    if os.path.exists(inventory_path):
        ansible_loader = DataLoader()
        ansible_inventory = InventoryManager(loader=ansible_loader,
                                             sources=inventory_path)
        package_choices = ansible_inventory.hosts.keys()
    return package_choices


def main():
    inventory_path = os.path.join(os.getcwd(), 'package_manifest.yaml')

    package_choices = find_packages(inventory_path)

    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--extra-vars',
                        dest="extra_vars",
                        action="append",
                        default=[],
                        help="""set additional variables as key=value or
                        YAML/JSON, if filename prepend with @""")
    parser.add_argument("-v", "--verbose",
                        action="count",
                        dest="verbose",
                        help="verbose output")
    parser.add_argument("--start-at-task",
                        action="store",
                        dest="start_at_task",
                        help="Start at a specific task")
    parser.add_argument("--step",
                        action="store_true",
                        dest="step",
                        default=False,
                        help="interactive: confirm each task before running")
    parser.add_argument("--list-tasks",
                        action="store_true",
                        dest="list_tasks",
                        default=False,
                        help="list tasks that will be run in the playbook")

    parser.add_argument("action",
                        choices=_PLAYBOOKS.keys(),
                        help="""which action to execute""")
    parser.add_argument('package',
                        metavar='package',
                        choices=package_choices,
                        help="the package to build")

    if argcomplete:
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    packaging_playbooks_path = resource_filename(__name__, 'data')
    playbook = _PLAYBOOKS[args.action]
    playbook_path = os.path.join(packaging_playbooks_path, playbook)
    cfg_path = os.path.join(packaging_playbooks_path, 'ansible.cfg')

    if os.path.exists(cfg_path):
        os.environ["ANSIBLE_CONFIG"] = cfg_path

    if not os.path.exists(inventory_path):
        print("Could not find your package_manifest.yaml")
        exit(1)
    if not os.path.exists(playbook_path):
        print("Could not find the packaging playbooks")
        exit(1)

    from ansible.cli.playbook import PlaybookCLI

    ansible_args = [playbook_path, '--inventory', inventory_path, '--limit',
                    args.package]
    for extra_var in args.extra_vars:
        ansible_args.extend(["-e", extra_var])
    if args.verbose:
        ansible_args.append("-%s" % str("v" * args.verbose))
    if args.start_at_task:
        ansible_args.append("--start-at-task")
        ansible_args.append(args.start_at_task)
    if args.step:
        ansible_args.append("--step")
    if args.list_tasks:
        ansible_args = ["--list-tasks"]

    ansible_playbook = (["ansible-playbook"] + ansible_args)

    if args.verbose:
        print(ansible_playbook)

    cli = PlaybookCLI(ansible_playbook)
    cli.parse()
    cli.run()


if __name__ == '__main__':
    main()
