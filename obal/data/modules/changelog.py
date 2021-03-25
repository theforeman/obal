# pylint: disable=C0111
import locale
import subprocess
import time
from contextlib import contextmanager

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.obal import get_specfile_evr  # pylint:disable=import-error,no-name-in-module

ANSIBLE_METADATA = {
    'metadata_version': '1.2',
    'status': ['preview'],
    'supported_by': 'community'
}


@contextmanager
def en_locale():
    """
    A context maanger that temporarily sets the LC_TIME locale to
    en_US.UTF-8 and then resets it.
    """
    try:
        locale.setlocale(locale.LC_TIME, "en_US.UTF-8")
    except locale.Error:
        yield
    else:
        try:
            yield
        finally:
            locale.resetlocale(locale.LC_TIME)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            spec=dict(required=True),
            entry=dict(required=False)
        )
    )

    spec = module.params['spec']
    entry = module.params['entry']

    user = subprocess.check_output(['rpmdev-packager'], universal_newlines=True).strip()
    evr = get_specfile_evr(spec)

    with open(spec) as spec_file:
        lines = spec_file.readlines()

    changed = False

    if entry and not entry.startswith('-'):
        entry = '- ' + entry

    for i, line in enumerate(lines):
        if line.startswith("%changelog"):
            if entry:
                with en_locale():
                    date = time.strftime("%a %b %d %Y", time.gmtime())
                entry = "* %s %s - %s\n%s\n\n" % (date, user, evr, entry)
                lines[i] += entry
                changed = True
            changelog = lines[i+1:]
            break

    if changed:
        with open(spec, "w") as spec_file:
            spec_file.writelines(lines)

    changelog = ''.join(changelog).rstrip()

    module.exit_json(changed=changed, changelog=changelog)


if __name__ == '__main__':
    main()
