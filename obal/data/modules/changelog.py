import subprocess
import time

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec = dict(
            spec = dict(required=True),
            changelog = dict(default='- rebuilt')
        )
    )

    spec = module.params['spec']
    changelog = module.params['changelog']

    user = subprocess.check_output(['rpmdev-packager']).strip()
    version = subprocess.check_output([
        'rpmspec',
        '--query',
        '--queryformat="%{version}"',
        '--srpm',
        spec
    ])
    release = subprocess.check_output([
        'rpmspec',
        '--query',
        '--queryformat="%{release}"',
        '--srpm',
        '--undefine=dist',
        spec
    ])

    release = release.strip().replace('"', '')
    version = version.strip().replace('"', '')

    with open(spec) as spec_file:
        lines = spec_file.readlines()

    changed = False

    for i, line in enumerate(lines):
        if line.startswith("%changelog"):
            date = time.strftime("%a %b %d %Y", time.gmtime())
            entry = "* %s %s %s-%s\n%s\n\n" % (date, user, version, release, changelog)
            lines[i] += entry
            changed = True
            break

    with open(spec, "w") as spec_file:
        spec_file.writelines(lines)

    module.exit_json(changed=changed)

if __name__ == '__main__':
    main()
