"""Record setup dependencies without installing packages on the test host."""

import json
import os

from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        names = self._task.args['name']
        with open(os.environ['OBAL_SETUP_LOG'], 'a') as stream:
            stream.write(json.dumps(names if isinstance(names, list) else [names]) + '\n')
        return {'changed': False}
