# obal - packaging wrapper using Ansible

[![Documentation Status](https://readthedocs.org/projects/obal/badge/?version=latest)](https://obal.readthedocs.io/en/latest/)

`obal` is an Ansible wrapper with a set of Ansible playbooks to ease maintanance of packaging repositories like [`foreman-packaging`](https://github.com/theforeman/foreman-packaging) and [`pulp-packaging`](https://github.com/pulp/pulp-packaging).

All `obal` actions should also work with plain Ansible when called like `ansible-playbook <action_playbook>.yml -l <package>` instead of `obal <action> <package>`.

## necessary tools

- `python` (2 or 3)
- `ansible`

## Using Obal via Container

Obal and all it's required packages are available in a container that can be used locally or in build environments. The users Koji credentials and configuration must be mounted into the container alongside of mounting the packaging project into `/opt/packaging` to work. Note the examples below assume SELinux is disabled.

To run (or sub `docker` for `podman`):

    podman run -v `pwd`:/opt/packaging -v ~/.koji:/root/.koji obal:latest scratch katello
