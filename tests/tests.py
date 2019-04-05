"""Tests for arg"""
import argparse
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import List, Union
from unittest import TestCase

import arg


class Datasets(Enum):
    OMNIGLOT = 'omniglot'
    MNIST = 'mnist'


@dataclass(frozen=True)
class Args:
    """Description."""
    missing_arg: int
    int_arg: int = arg.optional(100, help='Number of batches')
    default_int_arg: int = 30

    float_arg: float = 0.1
    default_float_arg: float = 0.1

    string_arg: str = 'hello'
    default_string_arg: str = 'hello'

    path_arg: Path = './save/proto-1'
    default_path_arg: Path = './save/proto-1'

    choice_arg: Datasets = Datasets.OMNIGLOT
    default_choice_arg: Datasets = 'omniglot'

    list_arg: List[int] = (1, 2, 3)
    default_list_arg: List[int] = (1, 2, 3)

    true_bool_arg: bool = True
    default_true_bool_arg: bool = True

    false_bool_arg: bool = False
    default_false_bool_arg: bool = False


class TestMissing(TestCase):
    def test_missing(self):
        self.assertRaises(
            TypeError,
            arg.parse_to, Args, args=[
                '--int-arg', '80',
                '--path-arg', './save/hello',
                '--choice-arg', 'mnist',
                '--float-arg', '0.2',
                '--string-arg', 'hi',
                '--list-arg', '3', '4', '5',
                '--no-true-bool-arg',
                '--false-bool-arg'])


class TestParse(TestCase):
    """Test argument parsing"""

    @classmethod
    def setUpClass(cls):
        cls.args: Args = arg.parse_to(
            Args, args=['--missing-arg', '80',
                        '--int-arg', '80',
                        '--path-arg', './save/hello',
                        '--choice-arg', 'mnist',
                        '--float-arg', '0.2',
                        '--string-arg', 'hi',
                        '--list-arg', '3', '4', '5',
                        '--no-true-bool-arg',
                        '--false-bool-arg'])

    def test_int_arg(self):
        """Test integer argument"""
        assert self.args.int_arg == 80
        assert self.args.default_int_arg == 30

    def test_path_arg(self):
        """Test path argument"""
        assert self.args.path_arg == Path('./save/hello')
        assert self.args.default_path_arg == Path('./save/proto-1')

    def test_choice_arg(self):
        """Test choice argument"""
        assert self.args.choice_arg == Datasets.MNIST
        assert self.args.default_choice_arg == Datasets.OMNIGLOT

    def test_float_arg(self):
        """Test float argument"""
        assert self.args.float_arg == 0.2
        assert self.args.default_float_arg == 0.1

    def test_str_arg(self):
        """Test string argument"""
        assert self.args.string_arg == 'hi'
        assert self.args.default_string_arg == 'hello'

    def test_list_arg(self):
        """Test list argument"""
        assert self.args.list_arg == [3, 4, 5]
        assert self.args.default_list_arg == (1, 2, 3)

    def test_bool_arg(self):
        """Test bool argument"""
        assert not self.args.true_bool_arg
        assert self.args.default_true_bool_arg
        assert self.args.false_bool_arg
        assert not self.args.default_false_bool_arg


def test_subparser():
    """Test subparser"""
    @dataclass
    class Args2:
        int_arg: int

    @dataclass
    class ComplexArg:
        args: Union[Args, Args2]

    parser = argparse.ArgumentParser()
    parser = arg.update_parser(ComplexArg, parser=parser)
    parsed = parser.parse_args('args --int-arg 80 --missing-arg 68'.split())
    assert isinstance(parsed, ComplexArg)
    assert isinstance(parsed.args, Args)

    parsed = parser.parse_args('args2 --int-arg 80'.split())
    assert isinstance(parsed, ComplexArg)
    assert isinstance(parsed.args, Args2)


def test_named_subparser():
    @dataclass
    class Args2:
        int_arg: int
        name = 'fancy_name'

    @dataclass
    class ComplexArg:
        args: Union[Args, Args2]

    parser = argparse.ArgumentParser()
    parser = arg.update_parser(ComplexArg, parser=parser)
    parser.parse_args('fancy_name --int-arg 80'.split())


def test_union():
    @dataclass
    class Args2:
        int_arg: int
        name = 'fancy_name'

    parser = argparse.ArgumentParser()
    parser = arg.update_parser(Union[Args, Args2], parser=parser)
    parser.parse_args('fancy_name --int-arg 80'.split())
