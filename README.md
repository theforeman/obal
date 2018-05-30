# obal - packaging wrapper using Ansible

`obal` is an Ansible wrapper with a set of Ansible playbooks to ease maintanance of packaging repositories like [`foreman-packaging`](https://github.com/theforeman/foreman-packaging) and [`pulp-packaging`](https://github.com/pulp/pulp-packaging).

All `obal` actions should also work with plain Ansible when called like `ansible-playbook <action_plaabook>.yml -l <package>` instead of `obal <action> <package>`.

## available action (playbooks)

### add

This action can add a new package from an upstream repo to a downstream onw, e.g. to add a package from `foreman-packaging` to a downstream product repository.

It's currently not possible to add a vanilla new package to `foreman-packaging`.

To add a new package from upstream, start by adding an entry to `package_manifest.yml` in the appropriate section (server, client, capsule, etc):

```yaml
my-new-package:
  upstream_files:
    - "my-new-package/"
```

The minimum fields required are the package's name and `upstream_files` which lists files to copy from the upstream repository. Entries in `upstream_files` can be file paths, or directories (denoted with a trailing slash).

```
obal add my-new-package
```

If all goes well, you should have a new directory in `packages/` containing the spec and any sources.

Sometimes `add` won't work due to your new packaging being in a non-standard location (in EPEL, for instance) then you'll need to do everything that `add_package.yml` does manually.

1. Create a directory for the spec and source(s)
1. Download the spec and source(s)
1. `git annex add` any binary source(s)
1. Edit the spec setting the release to `1`
1. Scratch build your package with `obal scratch new-manually-added-package`
1. If your scratch build is successful, then please commit your additions and submit an MR.

### check

This action verifies that the packages defined in git are also built into Koji/Brew/Copr.

### cleanup-copr

This action cleans up stale Copr scratch repos.

### release

This action releases a package to Koji/Brew/Copr (unless there is already the exact same version present).

### repoclosure

This action runs `repoclosure` for a repository, which ensures that all dependencies are met and all packages are installable.

### scratch

This action does a scratch build of a package.

### setup

This action installs packages required for proper `obal` usage on your machine.

### update

This action updates a package to a newer version. The newer version is either taken from an upstream repository or can be given via command line options

### bump-release

This action updates a spec file's release field and adds a pre-formatted changelog entry.

### lint

This action runs rpmlint on a spec file and reports the results.

#### Updating a Package from Upstream

To update a package from upstream, start by updating the `package_manifest.yml` entry for that package with the new versions and relevant information. Next run the update action specifying the package:

    obal update tfm-rubygem-hammer_cli

You can review the changes made by doing a `git status`. After making any manual changes, commit the changes and open an MR with the updates.

#### Updating a Package from Downstream

To update a package from downstream, no changes to `package_manifest.yml` are needed, just run the update action specifying the package and the correct downstream version:

    obal update tfm-rubygem-hammer_cli -e downstream_version=0.11.0.1

This will update the spec file to point to the `{{ source_server }}` location for source files and update the version to be what was provided. Then it will download the new source and add it to git annex.

You can review the changes made by doing a `git status`. After making any manual changes, commit the changes and open an MR with the updates.

The downstream section of the playbook also supports the following variables:

* `downstream_release`, defaults to `1`, if you ever have to bump the release only.
* `downstream_changelog_name`, defaults to `Satellite6 Jenkins`, the name used in the changelog entry.
* `downstream_changelog`, defaults to `- Release {{ inventory_hostname }} {{ downstream_version }}`, if you want to supply a custom changelog entry (can contain newlines).

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
