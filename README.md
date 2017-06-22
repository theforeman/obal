# Satellite Packaging

## new-6.3 required packages

- ansible

## Updating a Package from Upstream

To update a package from upstream, start by updating the `package_manifest.yml` entry for that package with the new versions and relevant information. Next run the update playbook specifying the package:

    ansible-playbook update_package.yml -l tfm-rubygem-hammer_cli

You can review the changes made by doing a `git status`. After making any manual changes, commit the changes and open an MR with the updates.

## Add a New Package from Upstream

To add a new package from upstream, start by adding an entry to `package_manifest.yml` in the appropriate section (server, client, capsule, etc):

```yaml
my-new-package:
  upstream_files:
    - "my-new-package/"
```

The minimum fields required are the package's name and `upstream_files` which lists files to copy from upstream to satellite-packaging. Entries in `upstream_files` can be file paths, or directories (denoted with a trailing slash).

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
