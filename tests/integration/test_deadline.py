import multiprocessing
import os
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from weather_lk.services.deadline import bounded_call
from weather_lk.services import deadline as deadline_module


def _start_child(marker):
    subprocess.run(
        [
            sys.executable,
            "-c",
            'import pathlib,sys,time; time.sleep(1.5); pathlib.Path(sys.argv[1]).write_text("leaked")',
            str(marker),
        ],
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def test_timeout_terminates_descendant_processes(tmp_path):
    marker = tmp_path / "child-finished"
    with pytest.raises(TimeoutError):
        bounded_call(_start_child, (marker,), time.monotonic() + 0.8)
    time.sleep(1.6)
    assert not marker.exists()


def test_production_worker_is_terminated_on_deadline():
    before = {process.pid for process in multiprocessing.active_children()}
    with pytest.raises(TimeoutError):
        bounded_call(time.sleep, (30,), time.monotonic() + 0.2)
    assert {process.pid for process in multiprocessing.active_children()} == before


def _leave_child(marker, abrupt_exit):
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
            'p.with_suffix(".started").write_text("ready"); '
            'time.sleep(1.5); p.write_text("leaked")',
            str(marker),
        ],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    deadline = time.monotonic() + 3
    while not marker.with_suffix(".started").exists():
        if child.poll() is not None or time.monotonic() >= deadline:
            raise RuntimeError("Test child failed to start")
        time.sleep(0.01)
    if abrupt_exit:
        os._exit(17)
    return "completed"


@pytest.mark.parametrize("abrupt_exit", [False, True])
def test_worker_exit_terminates_descendants(tmp_path, abrupt_exit):
    marker = tmp_path / "orphan-finished"
    if abrupt_exit:
        with pytest.raises(RuntimeError, match="without a result"):
            bounded_call(_leave_child, (marker, True), time.monotonic() + 5)
    else:
        assert (
            bounded_call(_leave_child, (marker, False), time.monotonic() + 5)
            == "completed"
        )
    assert marker.with_suffix(".started").exists()
    time.sleep(1.6)
    assert not marker.exists()


def test_containment_failure_does_not_start_target(monkeypatch):
    def denied():
        raise PermissionError("Job containment denied")

    # Invoke the worker directly with failing containment; never attach the
    # pytest process itself to a Windows job.
    monkeypatch.setattr(deadline_module, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(deadline_module, "_create_windows_job", denied)
    receiver, sender = multiprocessing.Pipe(duplex=False)
    calls = []
    try:
        deadline_module._process_worker(sender, lambda: calls.append("target"), ())
        assert receiver.recv() == (False, False, "Job containment denied")
        assert not calls
    finally:
        receiver.close()
        sender.close()


def test_group_cleanup_error_still_terminates_primary_worker(monkeypatch):
    def denied(*args):
        raise PermissionError("Group cleanup denied")

    # Exercise the cleanup error path on either platform while keeping the
    # spawned worker's actual containment and Process termination intact.
    monkeypatch.setattr(
        deadline_module, "os", SimpleNamespace(name="posix", killpg=denied)
    )
    monkeypatch.setattr(deadline_module, "signal", SimpleNamespace(SIGKILL=9))
    before = {process.pid for process in multiprocessing.active_children()}
    with pytest.raises(PermissionError, match="Group cleanup denied"):
        bounded_call(time.sleep, (30,), time.monotonic() + 0.4)
    assert {process.pid for process in multiprocessing.active_children()} == before
