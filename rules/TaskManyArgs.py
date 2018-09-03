# pylint: disable=C0103,C0111,R0903

from ansiblelint import AnsibleLintRule


class TaskManyArgs(AnsibleLintRule):
    id = 'E303'
    shortdesc = 'Use ":" YAML format when arguments are over 3'
    description = ''
    tags = ['task']

    def match(self, file, text):  # pylint: disable=R0201,W0613,W0622
        count = len([part for part in text.split(" ") if "=" in part])
        return count > 3
