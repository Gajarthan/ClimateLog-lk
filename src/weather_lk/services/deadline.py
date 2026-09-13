"""Bound external operations; terminate production workers on timeout."""

import multiprocessing
import os
import queue
import signal
import threading
import time


def _create_windows_job():
    """Attach this worker to a job that ends its descendants when it exits.

    The returned handle is intentionally left open until process exit. It is
    non-inheritable, so descendants cannot keep the job alive after the worker.
    See https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
    """
    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimits),
            ("IoInfo", ctypes.c_uint64 * 6),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.argtypes = ()
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL

    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = (
            0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        if not kernel.SetInformationJobObject(
            handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
            raise ctypes.WinError(ctypes.get_last_error())
    except BaseException:
        kernel.CloseHandle(handle)
        raise
    return handle


def _process_worker(connection, function, args):
    try:
        if os.name == "nt":
            # Do not run target code unless descendant containment succeeds.
            _job_handle = _create_windows_job()
        else:
            os.setsid()
        connection.send((True, function(*args)))
    except BaseException as error:
        connection.send((False, isinstance(error, ValueError), str(error)))
    finally:
        connection.close()


def bounded_call(function, args, deadline, isolated=True):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Run deadline reached")
    if not isolated:
        # Injectable pure functions may be local closures and cannot be spawned.
        results = queue.Queue(maxsize=1)

        def invoke():
            try:
                results.put((True, function(*args)))
            except BaseException as error:
                results.put((False, error))

        threading.Thread(target=invoke, daemon=True).start()
        try:
            success, result = results.get(timeout=remaining)
        except queue.Empty:
            raise TimeoutError("Run deadline reached") from None
        if not success:
            raise result
        return result
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    worker = context.Process(
        target=_process_worker, args=(sender, function, args), daemon=True
    )
    worker.start()
    sender.close()
    try:
        if not receiver.poll(max(0, deadline - time.monotonic())):
            raise TimeoutError("Run deadline reached")
        try:
            result = receiver.recv()
        except EOFError:
            raise RuntimeError("Worker exited without a result") from None
        if not result[0]:
            raise (ValueError if result[1] else RuntimeError)(result[2])
        if time.monotonic() >= deadline:
            raise TimeoutError("Run deadline reached")
        return result[1]
    finally:
        receiver.close()
        try:
            if os.name != "nt":
                try:
                    # Descendants may remain after the group leader has exited.
                    os.killpg(worker.pid, signal.SIGKILL)
                except ProcessLookupError:
                    # Before setsid(), no target code or children can run yet.
                    pass
        finally:
            try:
                if worker.is_alive():
                    worker.terminate()
                worker.join(timeout=5)
                if worker.is_alive():
                    worker.kill()
                    worker.join(timeout=5)
                if worker.is_alive():
                    raise RuntimeError("Worker could not be terminated")
            finally:
                if not worker.is_alive():
                    worker.close()
