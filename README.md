# obal - packaging wrapper using Ansible

[![Documentation Status](https://readthedocs.org/projects/obal/badge/?version=latest)](https://obal.readthedocs.io/en/latest/)

`obal` is an Ansible wrapper with a set of Ansible playbooks to ease maintanance of packaging repositories like [`foreman-packaging`](https://github.com/theforeman/foreman-packaging) and [`pulp-packaging`](https://github.com/pulp/pulp-packaging).

All `obal` actions should also work with plain Ansible when called like `ansible-playbook <action_playbook>.yml -l <package>` instead of `obal <action> <package>`.

## necessary tools

- `python` (2 or 3)
- `ansible`

## available options

Options can be either set on the command line via `-e key=val` or in the `package_manifest` file (preferred).

* `build_package_build_system`: which build system should be used, default: `koji`, supported: `koji`, `copr`
* `build_package_koji_command`: when using `koji` build system, which command to use to call it, default: `koji`, supported: `koji`, `brew`, anything else
* `build_package_tito_args`: any args that should be passed to `tito`, default: `''`
* `build_package_scratch`: when building a package, should a scratch build be done, default: `false` (unless you run `obal scratch`, of course)
* `build_package_test`: when building a package with `tito`, should `--test` be passed to it, default: `false`
* `build_package_tito_releaser_args`: any args that should be passed to `tito release`, default: `[]`
* `build_package_wait`: wait for package to be built on the build system, default: `true`
* `build_package_download_logs`: download build logs from the build system after the build has finished, default: `false`
* `diff_package_type`: which build system to query for built packages, default: `koji`, supported: `koji`, `copr`
* `diff_package_koji_command`: when using `koji` build system, which command to use to call it, default: `koji`, supported: `koji`, `brew`, anything else
* `diff_package_skip`: should packages be built without checking the build system, default: `true`
* `scl`: which SCL, if any, belong the packages to, defaults to `False` (no SCL)
