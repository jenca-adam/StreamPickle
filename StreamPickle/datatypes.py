import enum


class TypeDescr(enum.Enum):
    INT = 0
    FLOAT = 1
    BYTES = 2
    STR = 3
    TUPLE = 4
    LIST = 5
    SET = 6
    DICT = 7
    BOOL = 8
    FUNC = 9
    COMPLEX = 10
    TYPE = 11
    CODE = 12
    NONE = 13
    MAPPROXY = 14
    MEMVIEW = 15
    OBJ = 255
