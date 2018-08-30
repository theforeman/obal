class ObalArguments(object):
    @staticmethod
    def get_registry():
        registry = dict()
        SetupArguments.register(registry)
        registry['default'] = PackageArguments()
        return registry

    @staticmethod
    def add(config):
        registry = ObalArguments.get_registry()
        for action in config['actions']:
            action_subparser = config['subparsers'].add_parser(action, parents=config['parents'])
            if action in registry:
                registry[action].add_arguments(action_subparser, config)
            else:
                registry['default'].add_arguments(action_subparser, config)


class ActionArguments(object):
    action = ''

    @classmethod
    def register(cls, registry):
        if cls.action.strip() != '':
            registry[cls.action] = cls()

    def add_arguments(self, action_subparser, config):
        pass


class SetupArguments(ActionArguments):
    action = 'setup'


class PackageArguments(ActionArguments):
    def add_arguments(self, action_subparser, config):
        action_subparser.add_argument('package',
                                      metavar='package',
                                      choices=config['package_choices'],
                                      nargs='+',
                                      help="the package to build")


class ChangelogArguments(PackageArguments):
    action = 'changelog'

    def add_arguments(self, action_subparser, config):
        super(ChangelogArguments, self).add_arguments(action_subparser, config)
        action_subparser.add_argument('--changelog', help="The text for the changelog entry")
