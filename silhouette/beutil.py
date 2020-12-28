#!/usr/bin/env python

# Conversion utilities for printer's binary encoding commands
# (c) 2018 D. Bajar

from __future__ import print_function
import sys


def to_BE(x, y):
    if abs(x) < 112 and abs(y) < 112:
        index = 224 * (x + 112) + (y + 112)
        d2 = index // 224
        index -= d2 * 224
        d1 = index
        be1 = "%02X%02X" % (d1 + 0x20, d2 + 0x20)
        # print("BE1:", be1)
        return ("BE1", be1)
    elif abs(x) < 1676 and abs(y) < 1676:
        index = 3352 * (x + 1676) + (y + 1676)
        d3 = index // (224 * 224)
        index -= d3 * (224 * 224)
        d2 = index // 224
        index -= d2 * 224
        d1 = index
        be2 = "%02X%02X%02X" % (d1 + 0x20, d2 + 0x20, d3 + 0x20)
        # print("BE2:", be2)
        return ("BE2", be2)
    elif abs(x) < 375482 and abs(y) < 375482:
        index = 750964 * (x + 375482) + (y + 375482)
        d5 = index // (224 * 224 * 224 * 224)
        index -= d5 * (224 * 224 * 224 * 224)
        d4 = index // (224 * 224 * 224)
        index -= d4 * (224 * 224 * 224)
        d3 = index // (224 * 224)
        index -= d3 * (224 * 224)
        d2 = index // 224
        index -= d2 * 224
        d1 = index
        be3 = "%02X%02X%02X%02X%02X" % (d1 + 0x20, d2 + 0x20, d3 + 0x20, d4 + 0x20, d5 + 0x20)
        # print("BE3:", be3)
        return ("BE3", be3)
    else:
        raise ValueError("Invalid coordinate")
    # end if
# end def to_BE


def from_BE(be_stream):

    if len(be_stream) == 4:
        d1 = int(be_stream[:2], 16)
        d2 = int(be_stream[2:], 16)
        if d1 < 0x20 or d2 < 0x20:
            raise ValueError("Invalid BE1 stream digit")
        # end if
        index = (d2 - 0x20) * 224 + (d1 - 0x20)
        x = index // 224 - 112
        y = index % 224 - 112
        # print("BE1: %d,%d" % (x, y))
        return ("BE1", (x, y))
    elif len(be_stream) == 6:
        d1 = int(be_stream[0:2], 16)
        d2 = int(be_stream[2:4], 16)
        d3 = int(be_stream[4:6], 16)
        if d1 < 0x20 or d2 < 0x20 or d3 < 0x20:
            raise ValueError("Invalid BE2 stream digit")
        # end if
        index = (d3 - 0x20) * (224 * 224) + (d2 - 0x20) * 224 + (d1 - 0x20)
        x = index // 3352 - 1676
        y = index % 3352 - 1676
        # print("BE2: %d,%d" % (x, y))
        return ("BE2", (x, y))
    elif len(be_stream) == 10:
        d1 = int(be_stream[0:2], 16)
        d2 = int(be_stream[2:4], 16)
        d3 = int(be_stream[4:6], 16)
        d4 = int(be_stream[6:8], 16)
        d5 = int(be_stream[8:10], 16)
        if d1 < 0x20 or d2 < 0x20 or d3 < 0x20 or d4 < 0x20 or d5 < 0x20:
            raise ValueError("Invalid BE3 stream digit")
        # end if
        index = (d5 - 0x20) * (224 * 224 * 224 * 224) + (d4 - 0x20) * (224 * 224 * 224) + (d3 - 0x20) * (224 * 224) + (d2 - 0x20) * 224 + (d1 - 0x20)
        x = index // 750964 - 375482
        y = index % 750964 - 375482
        # print("BE3: %d,%d" % (x, y))
        return ("BE3", (x, y))
    else:
        raise ValueError("Invalid length hex stream")
    # end if

# end def from_BE


def test_BE(x, y, be_stream, be_enc):

    enc, stream = to_BE(x, y)
    passed = True if enc == be_enc and stream == be_stream else False
    print("to_BE: (%d, %d) -> '%s' %s= '%s' : %s" % (x, y, stream, '=' if passed else '!', be_stream, "PASSED" if passed else "FAILED"))
    if not passed:
        sys.exit(-1)
    # end if

    enc, xy = from_BE(be_stream)
    passed = True if enc == be_enc and xy == (x, y) else False
    print("from_BE: '%s -> (%d, %d) %s= (%d, %d) : %s" % (be_stream, xy[0], xy[1], '=' if passed else '!', x, y, "PASSED" if passed else "FAILED"))
    if not passed:
        sys.exit(-1)
    # end if

# end def test_BE


def test():

    print("Running tests ...")

    test_BE(   0,    0, "9090", "BE1")
    test_BE(   0,    1, "9190", "BE1")
    test_BE(   1,    0, "9091", "BE1")
    test_BE(   0,   -1, "8F90", "BE1")
    test_BE(  -1,    0, "908F", "BE1")
    test_BE(   1,    1, "9191", "BE1")
    test_BE(   1,   -1, "8F91", "BE1")
    test_BE(  -1,   -1, "8F8F", "BE1")
    test_BE(  -1,    1, "918F", "BE1")
    test_BE(   0,  111, "FF90", "BE1")
    test_BE( 111,    0, "90FF", "BE1")
    test_BE(  0,  -111, "2190", "BE1")
    test_BE(-111,    0, "9021", "BE1")
    test_BE( 111,  111, "FFFF", "BE1")
    test_BE( 111, -111, "21FF", "BE1")
    test_BE(-111, -111, "2121", "BE1")
    test_BE(-111,  111, "FF21", "BE1")
    test_BE(  56,  -27, "75C8", "BE1")
    test_BE( -77,   44, "BC43", "BE1")
    test_BE( -39,  106, "FA69", "BE1")
    test_BE(  72,  -25, "77D8", "BE1")

    test_BE(    0,   112, "3C2090", "BE2")
    test_BE(  112,     0, "AC8B97", "BE2")
    test_BE(    0,  -112, "3CFF8F", "BE2")
    test_BE( -112,     0, "AC9388", "BE2")
    test_BE(  112,   112, "3C8C97", "BE2")
    test_BE(  112,  -112, "3C8B97", "BE2")
    test_BE( -112,  -112, "3C9388", "BE2")
    test_BE( -112,   112, "3C9488", "BE2")
    test_BE(    0,  1675, "372790", "BE2")
    test_BE( 1675,     0, "D4E8FF", "BE2")
    test_BE(    0, -1675, "41F88F", "BE2")
    test_BE(-1675,     0, "843620", "BE2")
    test_BE( 1675,  1675, "5FF0FF", "BE2")
    test_BE( 1675, -1675, "69E1FF", "BE2")
    test_BE(-1675, -1675, "F92E20", "BE2")
    test_BE(-1675,  1675, "EF3D20", "BE2")
    test_BE( 1091,   674, "B6E8D8", "BE2")
    test_BE(  116,  1421, "D9CD97", "BE2")
    test_BE( -702,   485, "E13861", "BE2")
    test_BE(-1463, -1153, "C3552E", "BE2")

    print("All test PASSED !!!")
    sys.exit(0)

# end def test


def main(argv):

    # test()

    if len(argv) <= 1:
        print("Usage: %s <hex stream> | <x> <y>" % (argv[0]))
        return 1
    # end if

    if len(argv) <= 2:
        be_stream = argv[1]
        res = from_BE(be_stream)
        print("%s %s -> %d,%d" % (res[0], be_stream, res[1][0], res[1][1]))
    else:
        x = int(argv[1], 0)
        y = int(argv[2], 0)
        res = to_BE(x, y)
        print("%d,%d -> %s %s" % (x, y, res[0], res[1]))
    # end if

    return 0

# end def main


if __name__ == '__main__':
    sys.exit(main(sys.argv))
# end if
