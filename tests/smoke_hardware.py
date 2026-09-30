"""Hardware smoke test for the batched magnet snapshot. READ-ONLY: never ramps
or changes the field. Run with the LTSPM3 GUI closed and no other
Multi-Axis-Operation.exe running:

    cd C:\\Coding\\VectorMagnetControl
    python tests\\smoke_hardware.py

Starts its own Multi-Axis program, connects, exercises getStateSnapshot in both
modes, checks stability and error handling, disconnects and exits the program.
Prints PASS/FAIL per check and an overall verdict; exit code 1 on failure.
"""
import math
import sys
import time

from MultiAxisClass.vectorMagnet import vectorMagnet

FIELD_KEYS = ('r', 'phi', 'theta', 'rTarget', 'phiTarget', 'thetaTarget')
results = []


def check(name, cond, detail=''):
    cond = bool(cond)
    results.append(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}  {detail}")
    return cond


def drain_errors(m):
    """Pop and print every queued instrument error (one per 1 s tick)."""
    time.sleep(1.1)
    n = m.getErrorCount()
    while n > 0:
        print('   popped instrument error:', m.getError())
        time.sleep(1.1)
        n = m.getErrorCount()


def main():
    m = vectorMagnet()
    print('config :', m.multiAxisConfig)
    m.initialize_program()
    time.sleep(2)
    check('Multi-Axis program started', m.isAlive())
    m.loadSettings(m.multiAxisConfig)
    time.sleep(2)
    state = m.connect()
    time.sleep(1)
    check('connected (state 1/2/3/5)', state in (1, 2, 3, 5), f'state={state} {vectorMagnet.STATE_NAMES.get(state)}')
    print('IDN    :', m.getIDN())

    # --- batched snapshot: speed and values ---
    t0 = time.time()
    s = m.getStateSnapshot()
    dt = time.time() - t0
    print('batched:', s)
    check('batched snapshot under 0.5 s', dt < 0.5, f'{dt:.3f} s')
    check('batched values finite', all(math.isfinite(s[k]) for k in FIELD_KEYS))
    check('no instrument error during batched read', s['errorString'] == '', repr(s['errorString']))
    check('state in snapshot matches connect', s['state'] == m.getState())

    # --- sequential (legacy getters) agrees ---
    t0 = time.time()
    q = m.getStateSnapshot('sequential')
    dt2 = time.time() - t0
    print('sequential:', q, f'({dt2:.1f} s)')
    check('sequential agrees with batched',
          all(abs(s[k] - q[k]) < 1e-6 for k in FIELD_KEYS) and s['state'] == q['state']
          and s['persistent'] == q['persistent'])
    f = m.getFieldSpherical()
    check('legacy getFieldSpherical agrees', all(abs(a - b) < 1e-6 for a, b in zip(f, (s['r'], s['phi'], s['theta']))), str(f))

    # --- stability: 20 rapid batched snapshots ---
    bad = 0
    t0 = time.time()
    for _ in range(20):
        r = m.getStateSnapshot()
        if r['errorString'] or not all(math.isfinite(r[k]) for k in FIELD_KEYS):
            bad += 1
        time.sleep(0.2)
    per = (time.time() - t0) / 20 - 0.2
    time.sleep(1.1)
    check('20 rapid snapshots clean', bad == 0 and m.getErrorCount() == 0, f'{bad} bad, {per:.3f} s each, error count {m.getErrorCount()}')

    # --- session info ---
    info = m.getSessionInfo()
    print('session:', info)
    check('session info complete', info['idn'] != '' and info['units'] in (0, 1) and info['errorString'] == '',
          f"units={info['unitsName']!r} errors={info['errorString']!r}")

    # --- what an invalid query does (informational; drives the timeout path) ---
    m.replyTimeout = 3.0
    try:
        rep = m._sendUnsafeQuery(b'BOGUS')
        print(f'invalid query: program replied {rep!r}')
    except Exception as e:
        print(f'invalid query: no reply line, driver raised: {e}')
    drain_errors(m)
    check('error queue clean after invalid query', m.getErrorCount() == 0)

    # --- disconnected path ---
    m.disconnect()
    time.sleep(1.5)
    s0 = m.getStateSnapshot()
    print('disconnected snapshot:', s0)
    check('disconnected: state 0, NaN field, no exception', s0['state'] == 0 and math.isnan(s0['r']))

    # --- exit ---
    m.exit_program()
    time.sleep(1.5)
    check('program exited, isAlive false', not m.isAlive())

    overall = all(results)
    print(f'\nOVERALL: {"PASS" if overall else "FAIL"}  ({sum(results)}/{len(results)} checks)')
    return 0 if overall else 1


if __name__ == '__main__':
    sys.exit(main())
