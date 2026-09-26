#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

"""
Obal is a wrapper around Ansible playbooks. They are exposed as a command line application.
"""

from __future__ import print_function

import argparse
import os
import sys
from importlib import resources

import obsah
import yaml


class ApplicationConfig(obsah.ApplicationConfig):
    """
    A class describing the where to find various files
    """

    @staticmethod
    def name():
        """
        Return the name as shown to the user in the ArgumentParser
        """
        return 'obal'

    @staticmethod
    def target_names():
        """
        Return the name of the target in the playbook if the playbook takes a parameter.
        """
        return ['packages', 'copr_projects']

    @staticmethod
    def metadata_name():
        """
        Return the name of the metadata file.
        """
        return 'metadata.obal.yaml'

    @staticmethod
    def data_path():
        """
        Return the data path. Houses playbooks and configs.
        """
        path = os.environ.get('OBAL_DATA')
        if path is None:
            path = str(resources.files(__name__) / 'data')

        return path

    @staticmethod
    def inventory_path():
        """
        Return the inventory path
        """
        return os.environ.get('OBAL_INVENTORY', os.path.join(os.getcwd(), 'package_manifest.yaml'))


def _group_hosts(group_name, group_data, inventory, visited):
    if group_name in visited:
        return set()
    visited.add(group_name)

    if not isinstance(group_data, dict):
        return set()

    hosts = group_data.get('hosts', {})
    package_names = set(hosts if isinstance(hosts, (dict, list)) else [])

    children = group_data.get('children', {})
    child_names = children if isinstance(children, (dict, list)) else []
    for child_name in child_names:
        child_data = inventory.get(child_name)
        if child_data is None and isinstance(children, dict):
            child_data = children[child_name]
        package_names.update(_group_hosts(child_name, child_data, inventory, visited))

    return package_names


def load_package_names(inventory_path):
    """
    Load package names from the packages inventory group and its children.
    """
    with open(inventory_path, encoding='utf-8') as inventory_file:
        inventory = yaml.safe_load(inventory_file) or {}

    if not isinstance(inventory, dict):
        raise ValueError('the inventory must contain a YAML mapping')

    return sorted(_group_hosts('packages', inventory.get('packages', {}), inventory, set()))


def list_packages(cliargs, application_config):
    """
    Print the packages available in the configured package manifest.
    """
    parser = argparse.ArgumentParser(
        prog='{} list-packages'.format(application_config.name()),
        description='List packages available in package_manifest.yaml',
    )
    parser.parse_args(cliargs)

    inventory_path = application_config.inventory_path()
    try:
        packages = load_package_names(inventory_path)
    except (OSError, ValueError, yaml.YAMLError) as error:
        parser.exit(1, "Could not read package inventory '{}': {}\n".format(inventory_path, error))

    if packages:
        print('\n'.join(packages))


def main(cliargs=None, application_config=ApplicationConfig):  # pylint: disable=R0914
    """
    Main command
    """
    args = sys.argv[1:] if cliargs is None else cliargs
    if args[:1] == ['list-packages']:
        return list_packages(args[1:], application_config)

    return obsah.main(cliargs=args, application_config=application_config)


if __name__ == '__main__':
    main()
