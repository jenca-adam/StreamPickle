from .leb128 import leb128_encodeinto
from .datatypes import TypeDescr
import typing
from types import FunctionType, CodeType, NoneType, MappingProxyType
from collections.abc import Collection
import struct
import inspect
from io import BytesIO
import copyreg

# common dumps


def _dump_int(obj: int, stream: typing.IO) -> typing.NoReturn:
    leb128_encodeinto(obj, stream, signed=True)


def _dump_float(obj: float, stream: typing.IO) -> typing.NoReturn:
    stream.write(struct.pack("d", obj))  # 8 bytes


def _dump_complex(obj: complex, stream: typing.IO) -> typing.NoReturn:
    _dump_float(obj.real, stream)
    _dump_float(obj.imag, stream)


def _dump_bytes(obj: bytes, stream: typing.IO) -> typing.NoReturn:
    l = len(obj)
    leb128_encodeinto(l, stream, signed=False)
    stream.write(obj)


def _dump_str(obj: str, stream: typing.IO) -> typing.NoReturn:
    obj_bytes = obj.encode("utf-8")
    l = len(obj_bytes)
    leb128_encodeinto(l, stream, signed=False)
    stream.write(obj_bytes)


def _dump_sequence(obj: Collection, stream: typing.IO) -> typing.NoReturn:
    l = len(obj)
    leb128_encodeinto(l, stream, signed=False)
    for item in obj:
        dump(item, stream)


def _dump_bool(obj: bool, stream: typing.IO) -> typing.NoReturn:
    if obj:
        stream.write(b"\x01")
    else:
        stream.write(b"\x00")


def _dump_dict(obj: dict, stream: typing.IO) -> typing.NoReturn:
    l = len(obj)
    leb128_encodeinto(l, stream, signed=False)
    for key, value in obj.items():
        dump(key, stream)
        dump(value, stream)


# kinda useless dumps
def _dump_none(obj: NoneType, stream: typing.IO) -> typing.NoReturn:
    pass  # literally do nothing


def _dump_bytearray(obj: bytearray, stream: typing.IO) -> typing.NoReturn:

    _dump_bytes(bytes(obj))


def _dump_memoryview(obj: memoryview, stream: typing.IO) -> typing.NoReturn:
    _dump_str(obj.format, stream)
    _dump_bytes(obj.tobytes(), stream)


def _dump_code(obj: CodeType, stream: typing.IO) -> typing.NoReturn:
    _dump_int(obj.co_argcount, stream)
    _dump_int(obj.co_posonlyargcount, stream)
    _dump_int(obj.co_kwonlyargcount, stream)
    _dump_int(obj.co_nlocals, stream)
    _dump_int(obj.co_stacksize, stream)
    _dump_int(obj.co_flags, stream)
    _dump_bytes(obj.co_code, stream)
    _dump_sequence(obj.co_consts, stream)
    _dump_sequence(obj.co_names, stream)
    _dump_sequence(obj.co_varnames, stream)
    _dump_str(obj.co_filename, stream)
    _dump_str(obj.co_name, stream)
    _dump_str(obj.co_qualname, stream)
    _dump_int(obj.co_firstlineno, stream)
    _dump_bytes(obj.co_linetable, stream)
    _dump_bytes(obj.co_exceptiontable, stream)
    _dump_sequence(obj.co_freevars, stream)
    _dump_sequence(obj.co_cellvars, stream)


def _dump_function(obj: FunctionType, stream: typing.IO) -> typing.NoReturn:
    if not hasattr(obj, "__code__"):
        raise ValueError("dumping of builtin functions is not supported")
    fn_globals = getattr(obj, "__globals__", {})
    # _dump_dict(fn_globals, stream)
    _dump_code(obj.__code__, stream)  # dump code

    _dump_str(obj.__name__, stream)

def _dump_type(obj: type, stream: typing.IO) -> typing.NoReturn:
    _dump_str(obj.__module__, stream)
    _dump_str(obj.__name__, stream)


def _dump_object(
    obj: object, stream: typing.IO, attrs_only: bool = True
) -> typing.NoReturn:
    # TODO: cyclic references???
    tp = type(obj)
    try:
        reconstructor ,r_args, *dct = obj.__reduce__()
    except:
        raise TypeError(
        f"dumping of {tp.__name__} objects is not supported"
        )
    if reconstructor != copyreg._reconstructor:
        dump(reconstructor, stream)
    else:
        dump(None, stream)
    _dump_sequence(r_args, stream)
    if dct:
        dump(dct[0], stream)
    else:
        dump(None, stream)
def dump(obj: object, stream: typing.IO) -> typing.NoReturn:
    tp = type(obj)
    if tp in DUMP_TYPES:
        encoder, descr = DUMP_TYPES[tp]
        stream.write(bytes([descr.value]))
        encoder(obj, stream)
    elif inspect.isclass(obj):
        stream.write(bytes([TypeDescr.TYPE.value]))
        _dump_type(obj, stream)
    else:
        stream.write(bytes([TypeDescr.OBJ.value]))
        _dump_object(obj, stream)


def dumps(obj: object) -> bytes:
    stream = BytesIO()
    dump(obj, stream)
    return stream.getvalue()


DUMP_TYPES = {
    int: (_dump_int, TypeDescr.INT),
    float: (_dump_float, TypeDescr.FLOAT),
    complex: (_dump_complex, TypeDescr.COMPLEX),
    bytes: (_dump_bytes, TypeDescr.BYTES),
    str: (_dump_str, TypeDescr.STR),
    tuple: (_dump_sequence, TypeDescr.TUPLE),
    list: (_dump_sequence, TypeDescr.LIST),
    set: (_dump_sequence, TypeDescr.SET),
    dict: (_dump_dict, TypeDescr.DICT),
    bool: (_dump_bool, TypeDescr.BOOL),
    memoryview: (_dump_memoryview, TypeDescr.MEMVIEW),
    NoneType: (_dump_none, TypeDescr.NONE),
    CodeType: (_dump_code, TypeDescr.CODE),
    FunctionType: (_dump_function, TypeDescr.FUNC),
    MappingProxyType: (_dump_dict, TypeDescr.MAPPROXY),
}
