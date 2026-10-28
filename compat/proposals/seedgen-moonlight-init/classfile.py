"""Read pinned class-file metadata only. No JVM, class loading or execution."""
from pathlib import Path
import struct
import zipfile


class ClassFile:
    def __init__(self, raw):
        self.raw, self.pos = raw, 8
        self.cp = [None] * self.u2()
        index = 1
        while index < len(self.cp):
            tag = self.u1()
            if tag == 1:
                size = self.u2()
                self.cp[index] = self.take(size).decode('utf-8', errors='replace')
            elif tag in (3, 4):
                self.take(4)
            elif tag in (5, 6):
                self.take(8)
                index += 1
            elif tag in (7, 8, 16, 19, 20):
                self.cp[index] = (tag, self.u2())
            elif tag in (9, 10, 11, 12, 17, 18):
                self.cp[index] = (tag, self.u2(), self.u2())
            elif tag == 15:
                self.cp[index] = (tag, self.u1(), self.u2())
            else:
                raise ValueError('Unknown constant type')
            index += 1
        self.flags, self.name, self.base = self.u2(), self.ref(self.u2()), self.ref(self.u2())
        self.take(2 * self.u2())
        self.fields, self.methods = self.members(), self.members()

    def take(self, size):
        result = self.raw[self.pos:self.pos + size]
        if len(result) != size:
            raise ValueError('Truncated class')
        self.pos += size
        return result

    def u1(self):
        return self.take(1)[0]

    def u2(self):
        return struct.unpack('>H', self.take(2))[0]

    def u4(self):
        return struct.unpack('>I', self.take(4))[0]

    def ref(self, index):
        value = self.cp[index]
        if isinstance(value, str):
            return value
        if value is None:
            return str(index)
        if value[0] in (7, 8, 16):
            return self.ref(value[1])
        if value[0] == 12:
            return self.ref(value[1]) + self.ref(value[2])
        if value[0] in (9, 10, 11):
            return self.ref(value[1]) + '.' + self.ref(value[2])
        return str(value)

    def members(self):
        result = []
        for _ in range(self.u2()):
            flags, name, desc = self.u2(), self.ref(self.u2()), self.ref(self.u2())
            attrs = {}
            for _ in range(self.u2()):
                key, size = self.ref(self.u2()), self.u4()
                attrs[key] = self.take(size)
            result.append((flags, name, desc, attrs))
        return result

    def instructions(self, attr):
        length = struct.unpack_from('>I', attr, 4)[0]
        code = attr[8:8 + length]
        pc = 0
        while pc < len(code):
            op, size = code[pc], 1
            if op in (16, 18, 188, 169) or 21 <= op <= 25 or 54 <= op <= 58:
                size = 2
            elif op in (17, 19, 20, 132, 187, 189, 192, 193, 198, 199) or 153 <= op <= 168 or 178 <= op <= 184:
                size = 3
            elif op in (185, 186, 200, 201):
                size = 5
            elif op == 197:
                size = 4
            elif op == 196:
                size = 6 if code[pc + 1] == 132 else 4
            elif op == 170:
                aligned = pc + 1 + ((-pc - 1) % 4)
                low, high = struct.unpack_from('>ii', code, aligned + 4)
                size = aligned - pc + 12 + 4 * (high - low + 1)
            elif op == 171:
                aligned = pc + 1 + ((-pc - 1) % 4)
                pairs = struct.unpack_from('>i', code, aligned + 4)[0]
                size = aligned - pc + 8 + 8 * pairs
            if op in (178, 179, 180, 181, 182, 183, 184, 185, 186):
                yield pc, hex(op), self.ref(struct.unpack_from('>H', code, pc + 1)[0])
            elif op in (18, 19):
                index = code[pc + 1] if op == 18 else struct.unpack_from('>H', code, pc + 1)[0]
                yield pc, 'CONST', self.ref(index)
            elif 153 <= op <= 168 or op in (198, 199):
                yield pc, hex(op), '->' + str(pc + struct.unpack_from('>h', code, pc + 1)[0])
            elif 172 <= op <= 177:
                yield pc, 'RETURN', hex(op)
            if not 0 < size <= len(code) - pc or op > 201:
                raise ValueError('Invalid instruction boundary')
            pc += size
        assert pc == len(code)
