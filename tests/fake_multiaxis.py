"""Stand-in for the Multi-Axis-Operation subprocess: scripted replies, no hardware.

Used by tests/test_vectorMagnetOffline.py (pytest) and by the LTSPM3 MATLAB test
testReadVectorMagnetStatePy.m. Attach it with
    m = vectorMagnet(); m.multiSubProcess = FakeMultiAxis(); m._startReader()
"""
import queue


class _Stdin:
    def __init__(self, fake):
        self.fake = fake
        self.buf = b''

    def write(self, data: bytes):
        self.buf += data

    def flush(self):
        while b'\n' in self.buf:
            line, self.buf = self.buf.split(b'\n', 1)
            self.fake.handle(line.strip())


class _Stdout:
    def __init__(self, fake):
        self.fake = fake

    def readline(self) -> bytes:
        return self.fake.out.get()      # blocks like a pipe; b'' once closed


class FakeMultiAxis:
    """Replies to the SCPI-like queries vectorMagnet sends."""

    def __init__(self, state: int = 3):
        self.out = queue.Queue()
        self.sent = []                  # every command line received, in order
        self.errors = []                # queued instrument errors (LIFO pop)
        self.silent = set()             # commands that produce no reply line
        self.dead = False
        self.state = state
        self.field = (0.09, -6.5, 56.5)
        self.target = (0.1, -6.0, 56.0)
        self.persistent = 0
        self.units = 1
        self.idn = 'AMI,Multi-Axis,FAKE,1.0'
        self.align = {1: (0.03846, -7.0, 54.25), 2: (0.09, -6.5, 56.5)}
        self.stdin = _Stdin(self)
        self.stdout = _Stdout(self)

    # --- subprocess.Popen look-alikes ---
    def poll(self):
        return 0 if self.dead else None

    def close(self):
        self.dead = True
        self.out.put(b'')

    # --- helpers for tests (str arguments so MATLAB can call them) ---
    def make_silent(self, command: str):
        self.silent.add(command.encode('ascii'))

    def push_error(self, text: str):
        self.errors.append(text)

    def sent_commands(self) -> list:
        return [c.decode('ascii') for c in self.sent]

    # --- protocol ---
    def _reply(self, cmd: bytes):
        if cmd == b'STATE?':
            return b'%d' % self.state
        if cmd == b'FIELD?':
            return ('%g,%g,%g' % self.field).encode('ascii')
        if cmd == b'TARG?':
            return ('%g,%g,%g' % self.target).encode('ascii')
        if cmd == b'PERS?':
            return b'%d' % self.persistent
        if cmd == b'UNITS?':
            return b'%d' % self.units
        if cmd == b'*IDN?':
            return self.idn.encode('ascii')
        if cmd in (b'ALIGN1?', b'ALIGN2?'):
            return ('%g,%g,%g' % self.align[int(cmd[5:6])]).encode('ascii')
        if cmd == b'SYST:ERR:COUN?':
            return b'%d' % len(self.errors)
        if cmd == b'SYST:ERR?':
            return (self.errors.pop() if self.errors else '0,"No error"').encode('ascii')
        if cmd == b'*CLS':
            self.errors.clear()
            return None
        if cmd == b'EXIT':
            self.close()
            return None
        if cmd.endswith(b'?'):
            # unknown query: worst case, an error is queued and no reply line is emitted
            self.errors.append('-201,"Unrecognized query"')
            return None
        return None                     # commands have no reply

    def handle(self, cmd: bytes):
        self.sent.append(cmd)
        if cmd in self.silent:
            return
        reply = self._reply(cmd)
        if reply is not None:
            self.out.put(reply + b'\n')
