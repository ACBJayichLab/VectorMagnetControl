"""Offline tests for vectorMagnet: no hardware, the Multi-Axis process is faked.
Run from the repo root:  python -m pytest tests/test_vectorMagnetOffline.py -q
"""
import math
import time

import pytest

import MultiAxisClass.vectorMagnet as vmmod
from MultiAxisClass.vectorMagnet import vectorMagnet
from tests.fake_multiaxis import FakeMultiAxis


@pytest.fixture
def rig(monkeypatch):
    sleeps = []
    monkeypatch.setattr(vmmod.time, 'sleep', lambda s: sleeps.append(s))
    m = vectorMagnet()
    fake = FakeMultiAxis()
    m.multiSubProcess = fake
    m._startReader()
    m.replyTimeout = 0.5
    yield m, fake, sleeps
    fake.close()


def _is_flat(d):
    return all(isinstance(v, (float, int, bool, str)) and v is not None for v in d.values())


def test_snapshot_batched_values(rig):
    m, fake, sleeps = rig
    s = m.getStateSnapshot()
    assert (s['r'], s['phi'], s['theta']) == (0.09, -6.5, 56.5)
    assert (s['rTarget'], s['phiTarget'], s['thetaTarget']) == (0.1, -6.0, 56.0)
    assert s['state'] == 3 and s['persistent'] is False
    assert s['snapshotMode'] == 'batched' and s['errorString'] == ''
    assert abs(s['tRead'] - time.time()) < 5
    assert _is_flat(s)


def test_snapshot_batched_no_sleep_and_one_error_check(rig):
    m, fake, sleeps = rig
    m.getStateSnapshot()
    assert sleeps == []
    assert fake.sent_commands() == ['STATE?', 'FIELD?', 'TARG?', 'PERS?', 'SYST:ERR:COUN?']


def test_snapshot_sequential_matches_batched(rig):
    m, fake, sleeps = rig
    b = m.getStateSnapshot('batched')
    q = m.getStateSnapshot('sequential')
    for k in ('r', 'phi', 'theta', 'rTarget', 'phiTarget', 'thetaTarget', 'state', 'persistent'):
        assert b[k] == q[k]
    assert q['snapshotMode'] == 'sequential'
    assert len(sleeps) == 4            # one per legacy getter


def test_snapshot_disconnected_skips_field_queries(rig):
    m, fake, sleeps = rig
    fake.state = 0
    s = m.getStateSnapshot()
    assert s['state'] == 0 and math.isnan(s['r']) and math.isnan(s['rTarget'])
    assert fake.sent_commands() == ['STATE?']


def test_snapshot_quench_skips_field_queries(rig):
    m, fake, sleeps = rig
    fake.state = 6
    s = m.getStateSnapshot()
    assert s['state'] == 6 and fake.sent_commands() == ['STATE?']


def test_snapshot_queued_error_reported_not_raised(rig):
    m, fake, sleeps = rig
    fake.push_error('-301,"Not connected"')
    s = m.getStateSnapshot()
    assert s['errorString'] == '-301,"Not connected"'
    assert all(math.isnan(s[k]) for k in ('r', 'phi', 'theta', 'rTarget', 'phiTarget', 'thetaTarget'))
    assert s['state'] == 3
    assert fake.errors == []           # popped


def test_missing_reply_times_out(rig):
    m, fake, sleeps = rig
    fake.make_silent('FIELD?')
    t0 = time.time()
    with pytest.raises(Exception, match='Timed out|expected 3'):
        m.getStateSnapshot()
    assert time.time() - t0 < 2.0


def test_unknown_query_times_out_cleanly(rig):
    m, fake, sleeps = rig
    with pytest.raises(Exception, match='Timed out'):
        m._sendUnsafeQuery(b'BOGUS')
    assert m.getErrorCount() == 1


def test_isAlive_and_not_running(rig):
    m, fake, sleeps = rig
    assert m.isAlive()
    fake.close()
    assert not m.isAlive()
    with pytest.raises(Exception, match='not running'):
        m.getState()


def test_legacy_getters_unchanged(rig):
    m, fake, sleeps = rig
    f = m.getFieldSpherical()
    assert isinstance(f, tuple) and len(f) == 3 and f == (0.09, -6.5, 56.5)
    assert m.getState() == 3
    assert m.getPersistentMode() is False
    assert len(sleeps) == 3


def test_session_info_flat_and_correct(rig):
    m, fake, sleeps = rig
    info = m.getSessionInfo()
    assert _is_flat(info)
    assert info['idn'] == 'AMI,Multi-Axis,FAKE,1.0'
    assert info['units'] == 1 and info['unitsName'] == 'T'
    assert info['configPath'].endswith('.sav')
    assert (info['align1_r'], info['align1_phi'], info['align1_theta']) == (0.03846, -7.0, 54.25)
    assert info['errorString'] == ''


def test_session_info_tolerates_failures(rig):
    m, fake, sleeps = rig
    fake.make_silent('ALIGN2?')
    info = m.getSessionInfo()
    assert info['idn'] == 'AMI,Multi-Axis,FAKE,1.0'
    assert math.isnan(info['align2_r'])
    assert 'align2' in info['errorString']


def test_bad_mode_rejected(rig):
    m, fake, sleeps = rig
    with pytest.raises(ValueError):
        m.getStateSnapshot('fast')


def test_state_names_cover_all_codes():
    assert sorted(vectorMagnet.STATE_NAMES) == list(range(9))
