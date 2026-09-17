# SPDX-License-Identifier: AGPL-3.0-only
"""Exercise actual worker main limits in disposable OS processes, never in pytest."""

import json
import subprocess
import sys
from pathlib import Path

from app.science.ephemeris import identity, worker


def test_isolated_worker_and_parent_native_identity_agree():
    assert worker.BINARY_SHA256 == identity.BINARY_SHA256
    assert worker.BINARY_SIZE == identity.BINARY_SIZE


PROBE = """
import json, resource, runpy, sys
namespace = runpy.run_path(sys.argv[1])
def probe(utc, directory):
    mode = sys.argv[2]
    if mode == 'memory':
        try:
            value = bytearray(512 * 1024 * 1024)
        except MemoryError:
            return {'memory_blocked': True}
        return {'memory_blocked': False}
    if mode == 'cpu':
        while True:
            pass
    if mode == 'file':
        return {'oversize': 'x' * 16384}
    return {name: resource.getrlimit(getattr(resource, name)) for name in
            ('RLIMIT_CORE', 'RLIMIT_CPU', 'RLIMIT_AS', 'RLIMIT_FSIZE', 'RLIMIT_NOFILE')}
namespace['main'].__globals__['run'] = probe
namespace['main']()
"""


def probe(mode, output=subprocess.PIPE):
    return subprocess.run(
        [sys.executable, "-I", "-c", PROBE, str(Path(worker.__file__).resolve()), mode],
        input=b'{"utc":"2000-01-01T00:00:00+00:00"}',
        stdout=output,
        stderr=subprocess.PIPE,
        timeout=8,
        check=False,
    )


def test_actual_worker_main_installs_all_hard_and_soft_limits():
    result = probe("limits")
    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "RLIMIT_CORE": [0, 0],
        "RLIMIT_CPU": [2, 2],
        "RLIMIT_AS": [268435456, 268435456],
        "RLIMIT_FSIZE": [8192, 8192],
        "RLIMIT_NOFILE": [32, 32],
    }


def test_actual_worker_address_space_limit_rejects_allocation():
    result = probe("memory")
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"memory_blocked": True}


def test_actual_worker_cpu_limit_terminates_runaway_process():
    result = probe("cpu")
    assert result.returncode < 0
    assert not result.stdout


def test_actual_worker_file_size_limit_bounds_regular_file_output(tmp_path):
    target = tmp_path / "worker-output"
    with target.open("xb") as output:
        result = probe("file", output)
    assert result.returncode != 0
    assert target.stat().st_size <= 8192
