from io import BytesIO


def leb128_parsefrom(stream, signed=False):
    out = 0
    shift = 0

    while True:
        byte = stream.read(1)
        if not byte:
            raise EOFError("MSB set on last byte of input")
        value = byte[0]
        out |= (value & 0x7F) << shift
        shift += 7
        if not (value & 0x80):
            break
    if signed and (value & 0x40):
        out |= ~0 << shift
    return out


def leb128_encodeinto(i, stream, signed=False):
    if i < 0 and not signed:
        raise ValueError("can't encode negative integers as unsigned")
    while True:
        i, j = i >> 7, i & 0x7F
        if (
            signed
            and ((i == 0 and not j & 0x40) or (i == -1 and j & 0x40))
            or not signed
            and not i
        ):
            stream.write(bytes([j]))
            break
        else:
            stream.write(bytes([j | 0x80]))


def leb128_encode(i, signed=False):
    stream = BytesIO()
    leb128_encodeinto(i, stream, signed)
    return stream.getvalue()


def leb128_parse(data, signed=False):
    stream = BytesIO(data)
    return leb128_parsefrom(stream, signed)
