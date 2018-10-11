# obal - packaging wrapper using Ansible

[![Documentation Status](https://readthedocs.org/projects/obal/badge/?version=latest)](https://obal.readthedocs.io/en/latest/)

`obal` is an Ansible wrapper with a set of Ansible playbooks to ease maintanance of packaging repositories like [`foreman-packaging`](https://github.com/theforeman/foreman-packaging) and [`pulp-packaging`](https://github.com/pulp/pulp-packaging).

All `obal` actions should also work with plain Ansible when called like `ansible-playbook <action_playbook>.yml -l <package>` instead of `obal <action> <package>`.

## necessary tools

- `python` (2 or 3)
- `ansible`
