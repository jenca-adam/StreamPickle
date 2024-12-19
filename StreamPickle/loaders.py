from .leb128 import leb128_parsefrom
from .datatypes import TypeDescr
import struct
from collections.abc import Generator
from io import BytesIO
from types import CodeType, FunctionType, BuiltinFunctionType
import typing
import importlib
import copyreg

# Loaders for each type


def _load_int(stream: typing.IO) -> int:
    return leb128_parsefrom(stream, signed=True)


def _load_float(stream: typing.IO) -> float:
    b = stream.read(8)
    if len(b) < 8:
        raise EOFError("EOF while reading float")
    return struct.unpack("d", b)[0]


def _load_complex(stream: typing.IO) -> complex:
    real = _load_float(stream)
    imag = _load_float(stream)
    return complex(real, imag)


def _load_bytes(stream: typing.IO) -> bytes:
    l = leb128_parsefrom(stream, signed=False)
    b = stream.read(l)
    if len(b) < l:
        raise EOFError("EOF while reading bytes")
    return b


def _load_str(stream: typing.IO) -> str:
    l = leb128_parsefrom(stream, signed=False)
    b = stream.read(l)
    if len(b) < l:
        raise EOFError("EOF while reading str")
    return b.decode("utf-8")


def _load_sequence(stream: typing.IO) -> Generator[object, None, None]:
    l = leb128_parsefrom(stream, signed=False)
    items = []
    for _ in range(l):
        yield (load(stream))


def _load_bool(stream: typing.IO) -> bool:
    b = stream.read(1)
    if b not in b"\x00\x01":
        raise ValueError(f"invalid bool value: {b}")
    return b == b"\x01"


def _load_dict(stream: typing.IO) -> dict:
    l = leb128_parsefrom(stream, signed=False)
    d = {}
    for _ in range(l):
        key = load(stream)
        value = load(stream)
        d[key] = value
    return d


def _load_bytearray(stream: typing.IO) -> bytearray:
    return bytearray(_load_bytes(stream))


def _load_memoryview(stream: typing.IO) -> memoryview:
    fmt = _load_str(stream)
    b = _load_bytes(stream)
    return memoryview(b).cast(fmt)


def _load_code(stream: typing.IO) -> CodeType:
    return CodeType(
        _load_int(stream),
        _load_int(stream),
        _load_int(stream),
        _load_int(stream),
        _load_int(stream),
        _load_int(stream),
        _load_bytes(stream),
        tuple(_load_sequence(stream)),
        tuple(_load_sequence(stream)),
        tuple(_load_sequence(stream)),
        _load_str(stream),
        _load_str(stream),
        _load_str(stream),
        _load_int(stream),
        _load_bytes(stream),
        _load_bytes(stream),
        tuple(_load_sequence(stream)),
        tuple(_load_sequence(stream)),
    )


def _load_function(stream: typing.IO) -> FunctionType:
    return FunctionType(_load_code(stream), {}, _load_str(stream))


def _load_type(stream: typing.IO) -> type:
    module_name = _load_str(stream)
    qualname = _load_str(stream)
    module = importlib.import_module(module_name)
    return getattr(module, qualname)


def _load_object(stream: typing.IO) -> object:
    reconstructor = load(stream) or copyreg._reconstructor
    print(reconstructor)
    rec_args = tuple(_load_sequence(stream))
    state = load(stream)
    obj = reconstructor(*rec_args)
    if state is not None:
        if hasattr(obj, "__setstate__"):
            obj.__setstate__(state)
        else:
            obj.__dict__ = state
    return obj


def load(stream: typing.IO) -> object:
    td_byte = stream.read(1)[0]
    td = TypeDescr(td_byte)
    if td not in LOADERS:
        raise ValueError(f"Unsupported type descriptor: {td}")
    return LOADERS[td](stream)


def loads(b: bytes) -> object:
    stream = BytesIO(b)
    return load(stream)


LOADERS = {
    TypeDescr.INT: _load_int,
    TypeDescr.FLOAT: _load_float,
    TypeDescr.COMPLEX: _load_complex,
    TypeDescr.BYTES: _load_bytes,
    TypeDescr.STR: _load_str,
    TypeDescr.TUPLE: lambda stream: tuple(_load_sequence(stream)),
    TypeDescr.LIST: lambda stream: list(_load_sequence(stream)),
    TypeDescr.SET: lambda stream: set(_load_sequence(stream)),
    TypeDescr.DICT: _load_dict,
    TypeDescr.BOOL: _load_bool,
    TypeDescr.NONE: lambda stream: None,
    TypeDescr.CODE: _load_code,
    TypeDescr.FUNC: _load_function,
    TypeDescr.TYPE: _load_type,
    TypeDescr.OBJ: _load_object,
    TypeDescr.BLTIN_FUNC: _load_type, #tmp
    TypeDescr.MEMVIEW: _load_memoryview,
}
