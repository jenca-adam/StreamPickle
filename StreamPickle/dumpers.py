from .leb128 import leb128_encodeinto
from .datatypes import TypeDescr
import typing
from types import FunctionType, CodeType, NoneType, MappingProxyType, BuiltinFunctionType
from collections.abc import Collection
import struct
import inspect
from io import BytesIO
import copyreg
import importlib


class Dumper:
    def __init__(self, stream):
        self.stream = stream

    # common dumps
    def _dump_int(self, obj: int) -> typing.NoReturn:
        leb128_encodeinto(obj, self.stream, signed=True)

    def _dump_float(self, obj: float) -> typing.NoReturn:
        self.stream.write(struct.pack("d", obj))  # 8 bytes

    def _dump_complex(self, obj: complex) -> typing.NoReturn:
        self._dump_float(obj.real)
        self._dump_float(obj.imag)

    def _dump_bytes(self, obj: bytes) -> typing.NoReturn:
        l = len(obj)
        leb128_encodeinto(l, self.stream, signed=False)
        self.stream.write(obj)

    def _dump_str(self, obj: str) -> typing.NoReturn:
        obj_bytes = obj.encode("utf-8")
        l = len(obj_bytes)
        leb128_encodeinto(l, self.stream, signed=False)
        self.stream.write(obj_bytes)

    def _dump_sequence(self, obj: Collection) -> typing.NoReturn:
        l = len(obj)
        leb128_encodeinto(l, self.stream, signed=False)
        for item in obj:
            self.dump(item)

    def _dump_bool(self, obj: bool) -> typing.NoReturn:
        if obj:
            self.stream.write(b"\x01")
        else:
            self.stream.write(b"\x00")

    def _dump_dict(self, obj: dict) -> typing.NoReturn:
        l = len(obj)
        leb128_encodeinto(l, self.stream, signed=False)
        for key, value in obj.items():
            self.dump(key)
            self.dump(value)

    # kinda useless dumps
    def _dump_none(self, obj: NoneType) -> typing.NoReturn:
        pass  # literally do nothing

    def _dump_bytearray(self, obj: bytearray) -> typing.NoReturn:

        self._dump_bytes(bytes(obj))

    def _dump_memoryview(self, obj: memoryview) -> typing.NoReturn:
        self._dump_str(obj.format)
        self._dump_bytes(obj.tobytes())

    def _dump_code(self, obj: CodeType) -> typing.NoReturn:
        self._dump_int(obj.co_argcount)
        self._dump_int(obj.co_posonlyargcount)
        self._dump_int(obj.co_kwonlyargcount)
        self._dump_int(obj.co_nlocals)
        self._dump_int(obj.co_stacksize)
        self._dump_int(obj.co_flags)
        self._dump_bytes(obj.co_code)
        self._dump_sequence(obj.co_consts)
        self._dump_sequence(obj.co_names)
        self._dump_sequence(obj.co_varnames)
        self._dump_str(obj.co_filename)
        self._dump_str(obj.co_name)
        self._dump_str(obj.co_qualname)
        self._dump_int(obj.co_firstlineno)
        self._dump_bytes(obj.co_linetable)
        self._dump_bytes(obj.co_exceptiontable)
        self._dump_sequence(obj.co_freevars)
        self._dump_sequence(obj.co_cellvars)

    def _dump_function(self, obj: FunctionType) -> typing.NoReturn:
        if not hasattr(obj, "__code__"):
            raise ValueError(f"can't dump {obj.__name__}: no __code__")
        fn_globals = getattr(obj, "__globals__", {})
        # self._dump_dict(fn_globals, self.stream)
        self._dump_code(obj.__code__)  # dump code

        self._dump_str(obj.__name__)
    def _dump_builtin_function(self, obj:BuiltinFunctionType) ->typing.NoReturn:
        # since we can't dump code return module+name
        self._dump_str(obj.__module__)
        self._dump_str(obj.__name__)
    def _dump_type(self, obj: type) -> typing.NoReturn:
        self._dump_str(obj.__module__)
        self._dump_str(obj.__name__)

    def _dump_object(self, obj: object) -> typing.NoReturn:
        # TODO: cyclic references???
        tp = type(obj)
        try:
            reconstructor, r_args, *dct = obj.__reduce__()
            print(obj, reconstructor, r_args)
        except:
            raise TypeError(f"dumping of {tp.__name__} objects is not supported")
        if reconstructor != copyreg._reconstructor:
            self.dump(reconstructor)
        else:
            self.dump(None)
        self._dump_sequence(r_args)
        if dct:
            self.dump(dct[0])
        else:
            self.dump(None)

    def dump(self, obj: object) -> typing.NoReturn:
        tp = type(obj)
        if tp in self.DUMP_TYPES:
            encoder, descr = self.DUMP_TYPES[tp]
            self.stream.write(bytes([descr.value]))
            encoder(self,obj)
        elif inspect.isclass(obj):
            self.stream.write(bytes([TypeDescr.TYPE.value]))
            self._dump_type(obj)
        else:
            self.stream.write(bytes([TypeDescr.OBJ.value]))
            self._dump_object(obj)
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
        bytearray: (_dump_bytearray, TypeDescr.BARR),
        NoneType: (_dump_none, TypeDescr.NONE),
        CodeType: (_dump_code, TypeDescr.CODE),
        FunctionType: (_dump_function, TypeDescr.FUNC),
        BuiltinFunctionType: (_dump_builtin_function, TypeDescr.BLTIN_FUNC),
        MappingProxyType: (_dump_dict, TypeDescr.MAPPROXY),
    }


def dumps(obj: object) -> bytes:
    stream = BytesIO()
    dumper = Dumper(stream)
    dumper.dump(obj)
    return dumper.stream.getvalue()



