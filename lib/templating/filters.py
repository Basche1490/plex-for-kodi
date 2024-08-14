# coding=utf-8

import ibis
import copy
import operator
import six

from .util import register_builtin
from lib.aspectratio import v_ar_ratio
from lib.logging import log as LOG
from ibis.context import Undefined


@ibis.filters.register('get')
def get_attr(obj, attr, fallback=None, default=None):
    if isinstance(attr, Undefined):
        return obj.get(fallback, default)
    return obj.get(attr, default)


@ibis.filters.register('calc')
@register_builtin
def calc(a, b, op="add"):
    if isinstance(a, six.string_types):
        a = float(a) if "." in a else int(a)
    elif isinstance(b, six.string_types):
        b = float(b) if "." in b else int(b)
    try:
        return getattr(operator, op)(a, b)
    except:
        raise ValueError("Can't calculate {}({}:{}, {}:{})".format(op, type(a), repr(a), type(b), repr(b)))


@ibis.filters.register('vscale', with_context=True)
@register_builtin
def vscale(h, up=1, context=None):
    """
    scale integer based on the aspect ratio difference between the current resolution and our default resolution

    up is there to optionally apply a factor on top of the scaled value. this is important for buttons without a set
    width, as they tend to get crushed
    """
    if not context.core["needs_scaling"]:
        return h

    cached_scale = context.get('cached_scale', None)
    if cached_scale is None:
        w, h = context.core["resolution"]
        cached_scale = v_ar_ratio(w, h)
        context.set_global("cached_scale", cached_scale)
    return round(cached_scale * h, 2) * up


@ibis.filters.register('add')
@register_builtin
def add(a, b):
    return calc(a, b)


@ibis.filters.register('sub')
@register_builtin
def sub(a, b):
    return calc(a, b, op="sub")


@ibis.filters.register('div')
@register_builtin
def div(a, b):
    return calc(a, b, op="truediv")


@ibis.filters.register('mul')
@register_builtin
def mul(a, b):
    return calc(a, b, op="mul")


@ibis.filters.register('int')
@register_builtin
def cast_int(a):
    return int(a)


@ibis.filters.register('resolve', with_context=True)
@register_builtin('resolve')
def resolve_variable(arg, context=None):
    return ibis.nodes.ResolveContextVariable(arg)


@ibis.filters.register('merge_dict')
@ibis.filters.register('merge')
@register_builtin('merge')
def merge_dict(*args):
    final_dict = {}
    for arg in args:
        final_dict.update(copy.deepcopy(arg))

    return final_dict
