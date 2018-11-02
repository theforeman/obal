""""
Various argparse actions to convert command line parameters into their Ansible counter parts.
"""
# pylint: disable=too-few-public-methods,too-many-arguments
import argparse


class VariableAction(argparse.Action):
    """
    An action for argparse that stores all values in a shared dict.

    The dict is stored on the namespace as the value of NAMESPACE_DEST.
    """

    NAMESPACE_DEST = 'variables'

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            variables = getattr(namespace, self.NAMESPACE_DEST)
        except AttributeError:
            variables = {}
            setattr(namespace, self.NAMESPACE_DEST, variables)

        variables[self.dest] = values


class VariableConstAction(VariableAction):
    """
    An action that stores a constant when present.

    This mirrors the action='store' in regular argparse but is stored in a dict like
    VariableAction.
    """

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,  # pylint: disable=redefined-builtin
                 metavar=None):
        super(VariableConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        super(VariableConstAction, self).__call__(parser, namespace, self.const, option_string)


class VariableTrueAction(VariableConstAction):
    """
    An action that stores true when present
    """

    def __init__(self,
                 option_strings,
                 dest,
                 default=False,
                 required=False,
                 help=None):  # pylint: disable=redefined-builtin
        super(VariableTrueAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=True,
            default=default,
            required=required,
            help=help)


class VariableFalseAction(VariableConstAction):
    """
    An action that stores false when present
    """

    def __init__(self,
                 option_strings,
                 dest,
                 default=False,
                 required=False,
                 help=None):  # pylint: disable=redefined-builtin
        super(VariableFalseAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=False,
            default=default,
            required=required,
            help=help)


ACTION_MAP = {
    None: VariableAction,
    'store_true': VariableTrueAction,
    'store_false': VariableFalseAction,
}
