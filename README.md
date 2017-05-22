# Satellite Packaging

## new-6.3 required packages

- ansible

## Updating a Package from Upstream

To update a package from upstream, start by updating the `package_manifest.yml` entry for that package with the new versions and relevant information. Next run the update playbook specifying the package:

    ansible-playbook update_package.yml -l tfm-rubygem-hammer_cli

You can review the changes made by doing a `git status`. After making any manual changes, commit the changes and open an MR with the updates.

