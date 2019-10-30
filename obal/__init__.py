#!/usr/bin/env python2
# PYTHON_ARGCOMPLETE_OK

"""
Obal is a wrapper around Ansible playbooks. They are exposed as a command line application.
"""

from __future__ import print_function

import os
import obsah

import pkg_resources


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
    def target_name():
        """
        Return the name of the target in the playbook if the playbook takes a parameter.
        """
        return 'packages'

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
            path = pkg_resources.resource_filename(__name__, 'data')
            if not os.path.isabs(path):
                # this is essentially a workaround for
                # https://github.com/pytest-dev/pytest-xdist/issues/414
                distribution = pkg_resources.get_distribution('obal')
                path = os.path.join(distribution.location, path)

        return path

    @staticmethod
    def inventory_path():
        """
        Return the inventory path
        """
        return os.environ.get('OBAL_INVENTORY', os.path.join(os.getcwd(), 'package_manifest.yaml'))


def main(cliargs=None, application_config=ApplicationConfig):  # pylint: disable=R0914
    """
    Main command
    """
    obsah.main(cliargs=cliargs, application_config=application_config)


if __name__ == '__main__':
    main()
