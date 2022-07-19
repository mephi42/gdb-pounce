#!/usr/bin/env python3
import os
import re
import signal
from contextlib import contextmanager
from pwd import getpwuid
from shutil import copy, rmtree
from subprocess import PIPE, Popen, TimeoutExpired, check_call
from tempfile import mkdtemp
from unittest import TestCase, main

TASK_COMM_LEN = 16
RUNNING = b"Running, press Ctrl+C to stop...\n"
HELLO_WORLD = b"Hello, World!\n"
HELLO_FORK = b"Hello, Fork!\n"
HELLO_THREAD = b"Hello, Thread!\n"
GDB_ARGS_STR = "-ex 'handle SIGSTOP nostop noprint nopass'"
TEST_GDB_ARGS = ["-nx", "-batch", "-ex", "c", "-ex", "q"]
TEST_GDB_ARGS_STR = "-nx -batch -ex c -ex q"


class GdbPounceTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.basedir = os.path.dirname(__file__)
        cls.hello_c = os.path.join(cls.basedir, "hello.c")
        cls.gdb_pounce = os.path.join(cls.basedir, "..", "gdb-pounce")
        cls.workdir = mkdtemp()
        cls.hello = os.path.join(cls.workdir, "hello")
        check_call(["cc", "-o", cls.hello, cls.hello_c, "-pthread"])

    @classmethod
    def tearDownClass(cls):
        rmtree(cls.workdir)

    def expect_line(self, fp, exp):
        for line in fp:
            if isinstance(exp, re.Pattern):
                m = exp.match(line)
                if m is not None:
                    return m
            elif line == exp:
                return line
        else:
            self.fail()

    def expect_starting(self, gdb_pounce, gdb_args_str, exe):
        self.expect_line(
            gdb_pounce.stderr,
            f"Starting gdb -p {exe.pid} {GDB_ARGS_STR} {gdb_args_str}...\n".encode(),
        )

    def expect_skip_non_matching(self, gdb_pounce, exe, filtered_by):
        self.expect_line(
            gdb_pounce.stderr,
            f"Skipping non-matching pid {exe.pid} (filtered by {filtered_by})...\n".encode(),
        )

    def expect_gdb_exited(self, gdb_pounce):
        self.expect_line(gdb_pounce.stderr, b"GDB exited.\n")

    def expect_strace_exited(self, gdb_pounce):
        self.expect_line(gdb_pounce.stderr, b"strace exited.\n")

    @contextmanager
    def popen_gdb_pounce(self, args, strace=False):
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        gdb_pounce = Popen(
            [self.gdb_pounce] + (["--strace"] if strace else []) + args,
            stderr=PIPE,
            env=env,
        )
        try:
            self.expect_line(gdb_pounce.stderr, RUNNING)
            yield gdb_pounce
        finally:
            # Sometimes gdb-pounce swallows a SIGINT, so try in a loop.
            while True:
                os.kill(gdb_pounce.pid, signal.SIGINT)
                try:
                    returncode = gdb_pounce.wait(timeout=1)
                except TimeoutExpired:
                    continue
                break
            self.assertEqual(0, returncode)
            gdb_pounce.stderr.close()

    @contextmanager
    def popen_hello(self, args, fork=False, thread=False):
        exe = Popen(
            [self.hello]
            + (["--fork"] if fork else [])
            + (["--thread"] if thread else [])
            + args,
            stdout=PIPE,
        )
        try:
            yield exe
        finally:
            try:
                exp = HELLO_WORLD
                if fork:
                    exp += HELLO_FORK
                if thread:
                    exp += HELLO_THREAD
                self.assertEqual(exp, exe.stdout.read())
            finally:
                self.assertEqual(0, exe.wait())
                exe.stdout.close()

    def test_comm_collision(self):
        exe_path = os.path.join(self.workdir, "A" * TASK_COMM_LEN)
        copy(self.hello, exe_path)
        try:
            with self.popen_gdb_pounce(["A" * (TASK_COMM_LEN - 1)]) as gdb_pounce:
                exe = Popen([exe_path], stdout=PIPE)
                self.expect_skip_non_matching(gdb_pounce, exe, "Python")
                try:
                    self.assertEqual(HELLO_WORLD, exe.stdout.read())
                finally:
                    self.assertEqual(0, exe.wait())
                    exe.stdout.close()
        finally:
            os.unlink(exe_path)

    def test_matching_argv(self):
        with self.popen_gdb_pounce(TEST_GDB_ARGS + ["hello", "bar"]) as gdb_pounce:
            with self.popen_hello(["foo", "bar", "baz"]) as exe:
                self.expect_starting(gdb_pounce, TEST_GDB_ARGS_STR, exe)
            self.expect_gdb_exited(gdb_pounce)

    def test_fully_matching_argv(self):
        with self.popen_gdb_pounce(TEST_GDB_ARGS + ["hello", "A" * 2000]) as gdb_pounce:
            with self.popen_hello(["A" * 2000]) as exe:
                self.expect_starting(gdb_pounce, TEST_GDB_ARGS_STR, exe)
            self.expect_gdb_exited(gdb_pounce)

    def test_non_matching_argv(self):
        with self.popen_gdb_pounce(["hello", "quux"]) as gdb_pounce:
            with self.popen_hello(["foo", "bar", "baz"]) as exe:
                self.expect_skip_non_matching(gdb_pounce, exe, "BPF")

    def test_argv_collision(self):
        with self.popen_gdb_pounce(["hello", "quux", "xyzzy"]) as gdb_pounce:
            with self.popen_hello(["quzzy", "xyux"]) as exe:
                self.expect_skip_non_matching(gdb_pounce, exe, "Python")

    def test_matching_uid(self):
        with self.popen_gdb_pounce(
            [f"--uid={getpwuid(os.getuid())[0]}"] + TEST_GDB_ARGS + ["hello"]
        ) as gdb_pounce:
            with self.popen_hello([]) as exe:
                self.expect_starting(gdb_pounce, TEST_GDB_ARGS_STR, exe)
            self.expect_gdb_exited(gdb_pounce)

    def test_non_matching_uid(self):
        with self.popen_gdb_pounce(
            ["--uid", str(os.getuid() + 1), "hello"]
        ) as gdb_pounce:
            with self.popen_hello([]) as exe:
                self.expect_skip_non_matching(gdb_pounce, exe, "BPF")

    def test_fork(self):
        with self.popen_gdb_pounce(
            ["--fork"] + TEST_GDB_ARGS + ["hello"]
        ) as gdb_pounce:
            with self.popen_hello([], fork=True) as exe:
                m = self.expect_line(
                    gdb_pounce.stderr,
                    re.compile(
                        (
                            r"Starting gdb -p (\d+) "
                            + re.escape(f"{GDB_ARGS_STR} {TEST_GDB_ARGS_STR}...\n")
                        ).encode()
                    ),
                )
                (forked_pid_str,) = m.groups()
                self.assertNotEqual(int(forked_pid_str), exe.pid)
                self.expect_line(gdb_pounce.stderr, b"GDB exited.\n")

    def test_thread(self):
        with self.popen_gdb_pounce(["--fork", "hello"]):
            with self.popen_hello([], thread=True):
                pass

    def test_strace(self):
        with self.popen_gdb_pounce(["hello"], strace=True) as gdb_pounce:
            with self.popen_hello([]):
                self.expect_line(gdb_pounce.stderr, b"--- stopped by SIGSTOP ---\n")
                self.expect_line(gdb_pounce.stderr, b"+++ exited with 0 +++\n")
                self.expect_strace_exited(gdb_pounce)

    def test_symlink(self):
        symlink_path = os.path.join(self.workdir, "hello2")
        os.symlink("hello", symlink_path)
        try:
            with self.popen_gdb_pounce(TEST_GDB_ARGS + ["hello2"]) as gdb_pounce:
                exe = Popen([symlink_path], stdout=PIPE)
                self.expect_starting(gdb_pounce, TEST_GDB_ARGS_STR, exe)
                try:
                    self.assertEqual(HELLO_WORLD, exe.stdout.read())
                finally:
                    self.assertEqual(0, exe.wait())
                    exe.stdout.close()
        finally:
            os.unlink(symlink_path)

    def test_quit(self):
        with self.popen_gdb_pounce(
            ["-nx", "-batch", "-ex", "q", "hello"]
        ) as gdb_pounce:
            with self.popen_hello([]):
                pass
            self.expect_gdb_exited(gdb_pounce)
            self.expect_line(
                gdb_pounce.stderr,
                b"GDB left the process stopped - sending SIGCONT...\n",
            )


if __name__ == "__main__":
    main()
