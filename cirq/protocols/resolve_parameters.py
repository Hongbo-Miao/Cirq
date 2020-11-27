# Copyright 2018 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numbers
from typing import AbstractSet, Any, TypeVar, TYPE_CHECKING

import sympy
from typing_extensions import Protocol

from cirq import study
from cirq._doc import doc_private

if TYPE_CHECKING:
    import cirq

TDefault = TypeVar('TDefault')


class SupportsParameterization(Protocol):
    """An object that can be parameterized by Symbols and resolved
    via a ParamResolver"""

    @doc_private
    def _is_parameterized_(self: Any) -> bool:
        """Whether the object is parameterized by any Symbols that require
        resolution. Returns True if the object has any unresolved Symbols
        and False otherwise."""

    @doc_private
    def _parameter_names_(self: Any) -> AbstractSet[str]:
        """Returns a collection of string names of parameters that require
        resolution. If _is_parameterized_ is False, the collection is empty.
        The converse is not necessarily true, because some objects may report
        that they are parameterized when they contain symbolic constants which
        need to be evaluated, but no free symbols.
        """

    @doc_private
    def _resolve_parameters_(self: Any, param_resolver: 'cirq.ParamResolver',
                             recursive: bool):
        """Resolve the parameters in the effect."""


def is_parameterized(val: Any) -> bool:
    """Returns whether the object is parameterized with any Symbols.

    A value is parameterized when it has an `_is_parameterized_` method and
    that method returns a truthy value, or if the value is an instance of
    sympy.Basic.

    Returns:
        True if the gate has any unresolved Symbols
        and False otherwise. If no implementation of the magic
        method above exists or if that method returns NotImplemented,
        this will default to False.
    """
    if isinstance(val, sympy.Basic):
        return True
    if isinstance(val, numbers.Number):
        return False
    if isinstance(val, (list, tuple)):
        return any(is_parameterized(e) for e in val)

    getter = getattr(val, '_is_parameterized_', None)
    result = NotImplemented if getter is None else getter()

    if result is not NotImplemented:
        return result

    return bool(parameter_names(val))


def parameter_names(val: Any) -> AbstractSet[str]:
    """Returns parameter names for this object.

    Args:
        val: Object for which to find the parameter names.
        check_symbols: If true, fall back to calling parameter_symbols.

    Returns:
        A set of parameter names if the object is parameterized. It the object
        does not implement the _parameter_names_ magic method or that method
        returns NotImplemented, returns an empty set.
    """
    if isinstance(val, sympy.Basic):
        return {symbol.name for symbol in val.free_symbols}
    if isinstance(val, numbers.Number):
        return set()
    if isinstance(val, (list, tuple)):
        return {name for e in val for name in parameter_names(e)}

    getter = getattr(val, '_parameter_names_', None)
    result = NotImplemented if getter is None else getter()
    if result is not NotImplemented:
        return result

    return set()


def parameter_symbols(val: Any) -> AbstractSet[sympy.Symbol]:
    """Returns parameter symbols for this object.

    Args:
        val: Object for which to find the parameter symbols.

    Returns:
        A set of parameter symbols if the object is parameterized. It the object
        does not implement the _parameter_symbols_ magic method or that method
        returns NotImplemented, returns an empty set.
    """
    return {sympy.Symbol(name) for name in parameter_names(val)}


def resolve_parameters(
        val: Any,
        param_resolver: 'cirq.ParamResolverOrSimilarType') -> Any:
    """Resolves symbol parameters in the effect using the param resolver.

    This function will use the `_resolve_parameters_` magic method
    of `val` to resolve any Symbols with concrete values from the given
    parameter resolver.

    Args:
        val: The object to resolve (e.g. the gate, operation, etc)
        param_resolver: the object to use for resolving all symbols

    Returns:
        a gate or operation of the same type, but with all Symbols
        replaced with floats or terminal symbols according to the
        given ParamResolver. If `val` has no `_resolve_parameters_`
        method or if it returns NotImplemented, `val` itself is returned.

    Raises:
        RecursionError if the ParamResolver detects a loop in resolution.
    """
    if not param_resolver:
        return val

    # Ensure it is a dictionary wrapped in a ParamResolver.
    param_resolver = study.ParamResolver(param_resolver)
    if isinstance(val, sympy.Basic):
        return param_resolver.value_of(val)
    if isinstance(val, (list, tuple)):
        return type(val)(resolve_parameters(e, param_resolver) for e in val)

    getter = getattr(val, '_resolve_parameters_', None)
    result = (NotImplemented if getter is None else getter(param_resolver,
                                                           recursive=True))

    if result is not NotImplemented:
        return result
    else:
        return val


def resolve_parameters_once(val: Any,
                            param_resolver: 'cirq.ParamResolverOrSimilarType'
                           ) -> Any:
    """As resolve_parameters, but only performs one resolution step.

    This function will use the `_resolve_parameters_` magic method
    of `val` to resolve any Symbols with concrete values using a single
    step of the given parameter resolver.

    Args:
        val: The object to resolve (e.g. the gate, operation, etc)
        param_resolver: the object to use for resolving all symbols

    Returns:
        a gate or operation of the same type, but with all Symbols
        replaced with floats or terminal symbols according to the
        given ParamResolver. If `val` has no `_resolve_parameters_`
        method or if it returns NotImplemented, `val` itself is returned.
    """
    if not param_resolver:
        return val

    # Ensure it is a dictionary wrapped in a ParamResolver.
    param_resolver = study.ParamResolver(param_resolver)
    if isinstance(val, sympy.Basic):
        return param_resolver.value_of(val, recursive=False)
    if isinstance(val, (list, tuple)):
        return type(val)(
            resolve_parameters_once(e, param_resolver) for e in val)

    # TODO: untested and likely misbehaving
    getter = getattr(val, '_resolve_parameters_', None)
    result = (NotImplemented if getter is None else getter(param_resolver,
                                                           recursive=False))

    if result is not NotImplemented:
        return result
    else:
        return val
