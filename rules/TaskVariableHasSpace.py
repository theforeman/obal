# pylint: disable=C0103,C0111,R0903

import re

from ansiblelint import AnsibleLintRule


class TaskVariableHasSpace(AnsibleLintRule):
    id = 'E305'
    shortdesc = 'Variables should be enclosed by spaces "{{ foo }}"'
    description = ''
    tags = ['task']

    compiled = re.compile(r'{{(\w*)}}')

    def match(self, file, text):  # pylint: disable=R0201,W0613,W0622
        m = self.compiled.search(text)
        return bool(m)
