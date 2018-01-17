from ansiblelint import AnsibleLintRule

import re


class TaskVariableHasSpace(AnsibleLintRule):
    id = 'E305'
    shortdesc = 'Variables should be enclosed by spaces "{{ foo }}"'
    description = ''
    tags = ['task']

    compiled = re.compile('{{(\w*)}}')

    def match(self, file, text):
        m = self.compiled.search(text)
        return bool(m)
