# obal - packaging wrapper using ansible

## Updating a Package from Upstream

To update a package from upstream, start by updating the `package_manifest.yml` entry for that package with the new versions and relevant information. Next run the update action specifying the package:

    obal update tfm-rubygem-hammer_cli

This is equivalent to running the `update_package.yml` playbook:

    ansible-playbook --inventory package_manifest.yaml /path/to/obal/update_package.yml -l tfm-rubygem-hammer_cli

You can review the changes made by doing a `git status`. After making any manual changes, commit the changes and open an MR with the updates.

## Updating a Package from Downstream

To update a package from downstream, no changes to `package_manifest.yml` are needed, just run the update action specifying the package and the correct downstream version:

    obal update tfm-rubygem-hammer_cli -e downstream_version=0.11.0.1

This is equivalent to running the `update_package.yml` playbook:

    ansible-playbook --inventory package_manifest.yaml /path/to/obal/update_package.yml -l tfm-rubygem-hammer_cli -e downstream_version=0.11.0.1

This will update the spec file to point to the Dogfood location for source files and update the version to be what was provided. Then it will download the source from Dogfood and add it to git annex.

You can review the changes made by doing a `git status`. After making any manual changes, commit the changes and open an MR with the updates.

The downstream section of the playbook also supports the following variables:

* `downstream_release`, defaults to `1`, if you ever have to bump the release only.
* `downstream_changelog_name`, defaults to `Satellite6 Jenkins`, the name used in the changelog entry.
* `downstream_changelog`, defaults to `- Release {{ inventory_hostname }} {{ downstream_version }}`, if you want to supply a custom changelog entry (can contain newlines).

## Add a New Package from Upstream

To add a new package from upstream, start by adding an entry to `package_manifest.yml` in the appropriate section (server, client, capsule, etc):

```yaml
my-new-package:
  upstream_files:
    - "my-new-package/"
```

The minimum fields required are the package's name and `upstream_files` which lists files to copy from upstream to satellite-packaging. Entries in `upstream_files` can be file paths, or directories (denoted with a trailing slash).

```
obal add my-new-package
```

*OR*

```
ansible-playbook add_package.yml -l my-new-package
```

If all goes well, you should have a new directory in `packages/` containing the spec and any sources.

Sometimes `add_package.yml` won't work due to your new packaging being in a non-standard location (in EPEL, for instance) then you'll need to do everything that `add_package.yml` does manually.

1. Create a directory for the spec and source(s)
1. Download the spec and source(s)
1. `git annex add` any binary source(s)
1. Edit the spec setting the release to `1`
1. Scratch build your package with `ansible-playbook scratch_build.yml -l new-manually-added-package -t wait`
1. If your scratch build is successful, then please commit your additions and submit an MR.
