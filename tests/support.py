"""Host capabilities and owned temporary resources for the test suite."""

import errno
from functools import lru_cache
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


SHELL_REQUIRED = "native POSIX shell unavailable (Git for Windows or a POSIX host required)"


def remove_tree(path):
    path = os.fspath(path)
    if not path:
        return
    path = os.path.abspath(path)
    if not os.path.lexists(path):
        return
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        (os.rmdir if stat.S_ISDIR(info.st_mode) else os.unlink)(path)
        return

    retried = set()

    def writable_then_retry(function, name, exc):
        if isinstance(exc[1], FileNotFoundError):
            return
        if not isinstance(exc[1], PermissionError) or name in retried:
            raise exc[1]
        retried.add(name)
        if name != path:
            parent = os.path.dirname(name)
            info = os.lstat(parent)
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise exc[1]
            os.chmod(parent, stat.S_IMODE(info.st_mode) | stat.S_IRWXU)
        info = os.lstat(name)
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            (os.rmdir if stat.S_ISDIR(info.st_mode) else os.unlink)(name)
            return
        if stat.S_ISDIR(info.st_mode):
            os.chmod(name, stat.S_IMODE(info.st_mode) | stat.S_IRWXU)
            shutil.rmtree(name, onerror=writable_then_retry)
        else:
            os.chmod(name, stat.S_IMODE(info.st_mode) | stat.S_IRUSR | stat.S_IWUSR)
            function(name)

    # Python 3.8+ removes nested Windows junctions without traversing their targets.
    shutil.rmtree(path, onerror=writable_then_retry)


class TemporaryDirectory:
    def __init__(self, suffix=None, prefix=None, dir=None):
        self.name = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=dir)

    def __enter__(self):
        return self.name

    def __exit__(self, *exc):
        self.cleanup()

    def cleanup(self):
        remove_tree(self.name)


def shell_path(path):
    return os.fspath(path).replace("\\", "/") if os.name == "nt" else os.fspath(path)


@lru_cache(maxsize=None)
def find_shell(name="sh"):
    candidates = []
    git = shutil.which("git")
    if os.name == "nt" and git:
        for root in Path(git).resolve().parents:
            # bin/sh.exe prepends usr/bin and can hide deliberate PATH fixtures.
            candidates.extend(root / directory / (name + ".exe") for directory in ("usr/bin", "bin"))
    candidate = shutil.which(name)
    if candidate:
        candidates.append(Path(candidate))
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            probe = subprocess.run([str(candidate), "-c", 'test -f "$1"', "probe", shell_path(__file__)],
                                   capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0:
            return str(candidate)
    return None


def shell_tool(name):
    shell = find_shell()
    if shell is None:
        raise unittest.SkipTest(SHELL_REQUIRED)
    if os.name == "nt":
        for root in Path(shell).parents:
            for directory in ("usr/bin", "bin", "mingw64/bin", "cmd"):
                path = root / directory / (name + ".exe")
                if path.is_file():
                    return str(path)
    path = shutil.which(name)
    if path is None:
        raise unittest.SkipTest("shell utility unavailable: " + name)
    return path


def shell_wrapper(path, command):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("#!/bin/sh\n" + command + "\n")
    path.chmod(0o755)
    return path


def native_path(path):
    if os.name != "nt":
        return os.fspath(path)
    result = subprocess.run([shell_tool("cygpath"), "-w", os.fspath(path)],
                            check=True, capture_output=True, text=True)
    return result.stdout.rstrip("\r\n")


def shell_environment(directory, env=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    shell_wrapper(directory / "python3", "exec %s -B \"$@\"" % shlex.quote(shell_path(sys.executable)))
    env = dict(os.environ if env is None else env)
    paths = [str(directory)]
    shell = find_shell()
    if shell:
        paths.append(str(Path(shell).parent))
        if os.name == "nt":
            paths.append(str(Path(shell_tool("git")).parent))
    paths.append(env.get("PATH", ""))
    env.update(PATH=os.pathsep.join(paths), PYTHONDONTWRITEBYTECODE="1")
    return env


def require_symlinks(directory=False):
    with TemporaryDirectory() as root:
        target, link = Path(root, "target"), Path(root, "link")
        if directory:
            target.mkdir()
        else:
            target.write_bytes(b"probe")
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError as exc:
            if exc.errno not in (errno.EPERM, errno.EACCES, errno.ENOSYS, errno.ENOTSUP) and getattr(exc, "winerror", None) != 1314:
                raise
            kind = "directory" if directory else "file"
            raise unittest.SkipTest("%s symlinks unavailable (privilege or filesystem capability)" % kind)


def require_filename(name):
    with TemporaryDirectory() as directory:
        try:
            Path(directory, name).write_bytes(b"probe")
            if name in os.listdir(directory):
                return
        except OSError as exc:
            if exc.errno not in (errno.EINVAL, errno.ENOENT, errno.EACCES) and getattr(exc, "winerror", None) != 123:
                raise
        raise unittest.SkipTest("filesystem cannot represent literal filename %r" % name)


def require_executable_bits():
    with TemporaryDirectory() as root:
        path = Path(root, "mode-probe")
        path.write_bytes(b"probe")
        path.chmod(0o644)
        not_executable = not os.access(path, os.X_OK)
        path.chmod(0o755)
        if not not_executable or not os.access(path, os.X_OK):
            raise unittest.SkipTest("filesystem does not support POSIX executable-permission checks")


def make_junction(link, target):
    if os.name != "nt":
        raise unittest.SkipTest("Windows junction capability")
    result = subprocess.run([os.environ.get("COMSPEC", "cmd.exe"), "/c", "mklink", "/J", str(link), str(target)],
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("junction fixture creation failed: " + result.stdout + result.stderr)


def command_text(arguments):
    return subprocess.list2cmdline(arguments) if os.name == "nt" else " ".join(shlex.quote(arg) for arg in arguments)


def fake_command(directory, name, source):
    """Return an argv prefix without generating a new Windows executable."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / (name + ".py")
    script.write_text(source, encoding="utf-8")
    if os.name == "nt":
        return [sys.executable, "-B", str(script)]
    command = shell_wrapper(directory / name, "exec %s -B %s \"$@\"" %
                            (shlex.quote(sys.executable), shlex.quote(str(script))))
    return [str(command)]
