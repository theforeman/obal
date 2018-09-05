# pylint: disable=C0103,C0111,R0903

from ansiblelint import AnsibleLintRule


try:
    basestring
except NameError:  # Python 3 has no basestring
    basestring = str  # pylint: disable=W0622


def _is_invalid_hosts(hosts):
    try:
        iter(hosts)
    except TypeError:
        return True

    return isinstance(hosts, basestring)


class PlayHostsIsList(AnsibleLintRule):
    id = 'E306'
    shortdesc = 'Hosts in a play must be a list'
    description = ''
    tags = ['play']

    def matchplay(self, file, data):  # pylint: disable=W0622
        if file['type'] == 'playbook' and 'hosts' in data and _is_invalid_hosts(data['hosts']):
            return ({'hosts': data}, self.shortdesc)
        return None
