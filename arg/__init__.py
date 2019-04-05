"""
A set of tools to construct argument parsers.

Rules:
------

1. A dataclass is assigned a parser
2. int, float, str are registered as corresponding types
3. bool is transformed into store_true and store_false actions
4. Enum classes are registered as choice action
5. Union type is transformed into a set of subparsers recursively

"""
import argcomplete
import argparse
import copy
import dataclasses
import enum
from types import MethodType
from typing import List, Union


__all__ = ('parse_to',)


def add_arg(parser, mangler, name, dest=None, **kwargs):
    if dest is None:
        dest = name
    parser.add_argument(mangler(name), dest=dest, **kwargs)


def add_bool_arg(parser, mangler, name, **kwargs):
    kwargs.pop('type')
    add_arg(parser, lambda x: x, mangler(name), dest=name,
            action='store_true', **kwargs)
    add_arg(parser, lambda x: x, mangler(name, prefix='no'), dest=name,
            action='store_false', **kwargs)


def add_narg(parser, mangler, name, **kwargs):
    type, = kwargs.pop('type').__args__
    add_arg(parser, mangler, name,
            type=type, nargs=kwargs.pop('nargs', '*'), **kwargs)


def add_choice_arg(parser, mangler, name, **kwargs):
    add_arg(parser, mangler, name,
            choices=kwargs.pop('choices', list(kwargs['type'])), **kwargs)


def _wrap(parser):
    def construct_classes(arg_dict):
        klass = arg_dict.pop('return')
        children = set(k.split('.')[0]
                       for k in arg_dict if len(k.split('.')) == 2)
        for k, v in list(arg_dict.items()):
            if v is dataclasses.MISSING:
                arg_dict.pop(k)
        for child in children:
            child_dict = {'.'.join(k.split('.')[1:]): v
                          for k, v in arg_dict.items()
                          if k.split('.')[0] == child}
            for k in list(arg_dict.keys()):
                if k.split('.')[0] == child:
                    arg_dict.pop(k)
            arg_dict[child] = construct_classes(child_dict)
        if '' in arg_dict:
            return arg_dict.get('')
        return klass(**arg_dict)

    def parse_args(self, *args, **kwargs):
        parsed = vars(parser.parse_args(*args, **kwargs))
        return construct_classes(parsed)

    wrapper = copy.copy(parser)
    wrapper.parse_args = MethodType(parse_args, wrapper)

    return wrapper


def _optional_mangler(name: str, *, prefix: str = None):
    name = name.split('.')[-1]
    name = name.replace('_', '-')
    if prefix is not None:
        return f'--{prefix}-{name}'
    return f'--{name}'


def _positional_mangler(name: str, *, prefix: str = None):
    name = name.lower()
    if prefix is not None:
        return f'{prefix}_{name}'
    return name


def update_parser(container_class, parser=None,
                  optional_name_mangler=None,
                  positional_name_mangler=None,
                  prefix=None):
    if parser is None:
        parser = argparse.ArgumentParser(
            description=container_class.__doc__)
    parser.set_defaults(
        **{f"{prefix}.return" if prefix is not None
           else "return": container_class})

    if optional_name_mangler is None:
        optional_name_mangler = _optional_mangler

    if positional_name_mangler is None:
        positional_name_mangler = _positional_mangler

    if getattr(container_class, '__origin__', None) is Union:
        subparsers = parser.add_subparsers()
        full_name = prefix if prefix is not None else ""
        for klass in container_class.__args__:
            subparser = subparsers.add_parser(
                positional_name_mangler(
                    name=getattr(klass, 'name', klass.__name__)))
            prefix = full_name
            update_parser(klass, parser=subparser, prefix=prefix)
        return _wrap(parser)

    for field in dataclasses.fields(container_class):
        kwargs = dict(field.metadata,
                      type=field.type,
                      default=field.default)

        if kwargs.pop('optional', True):
            name_mangler = optional_name_mangler
        else:
            name_mangler = positional_name_mangler

        full_name = (f"{prefix}.{field.name}"
                     if prefix is not None else field.name)

        if kwargs['type'] is bool:
            add_bool_arg(parser, name_mangler, full_name, **kwargs)
        elif getattr(kwargs['type'], '__origin__', None) is List:
            add_narg(parser, name_mangler, full_name, **kwargs)
        elif getattr(kwargs['type'], '__origin__', None) is Union:
            update_parser(kwargs['type'], parser=parser, prefix=full_name)
        elif issubclass(kwargs['type'], enum.Enum):
            add_choice_arg(parser, name_mangler, full_name, **kwargs)
        else:
            add_arg(parser, name_mangler, full_name, **kwargs)

    return _wrap(parser)


def parse_to(container_class, **kwargs):
    parser = argparse.ArgumentParser(
        description=container_class.__doc__)

    parser = update_parser(container_class, parser=parser)

    argcomplete.autocomplete(parser)
    args: container_class = parser.parse_args(**kwargs)
    return args


def optional(default=dataclasses.MISSING, **kwargs):
    default_kwargs = dict(
        default=default, default_factory=dataclasses.MISSING,
        init=True, repr=True, hash=None, compare=True, metadata=None)
    new_kwargs = {name: kwargs.pop(name, default)
                  for name, default in default_kwargs.items()}
    if new_kwargs['metadata'] is None:
        new_kwargs['metadata'] = {}
    new_kwargs['metadata'].update(kwargs, optional=True)
    return dataclasses.field(**new_kwargs)


def positional(default=dataclasses.MISSING, **kwargs):
    default_kwargs = dict(
        default=default, default_factory=dataclasses.MISSING,
        init=True, repr=True, hash=None, compare=True, metadata=None)
    new_kwargs = {name: kwargs.pop(name, default)
                  for name, default in default_kwargs.items()}
    if new_kwargs['metadata'] is None:
        new_kwargs['metadata'] = {}
    new_kwargs['metadata'].update(kwargs, optional=False)
    return dataclasses.field(**new_kwargs)
