"""
Formatting tools for manifests
"""
from ruamel.yaml import YAML


def _get_yaml():
    yaml = YAML(typ='rt')
    yaml.default_flow_style = False
    yaml.explicit_start = True
    yaml.preserve_quotes = True
    yaml.indent(sequence=4, offset=2)
    return yaml


def reformat(manifest):
    """
    Reformat a manifest
    """
    # TODO: sort hosts
    return manifest


def load(stream):
    """
    Load a manifest from a stream
    """
    return _get_yaml().load(stream)


def write(manifest, stream):
    """
    Write a manifest to a stream
    """
    _get_yaml().dump(manifest, stream)
