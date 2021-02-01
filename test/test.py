#!/usr/bin/env python3
import os
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
GDB_ARGS = "-ex 'handle SIGSTOP nostop noprint nopass'"


class GdbPounceTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.basedir = os.path.dirname(__file__)
        cls.hello_c = os.path.join(cls.basedir, "hello.c")
        cls.gdb_pounce = os.path.join(cls.basedir, "..", "gdb-pounce")
        cls.workdir = mkdtemp()
        cls.hello = os.path.join(cls.workdir, "hello")
        check_call(["cc", "-o", cls.hello, cls.hello_c])

    @classmethod
    def tearDownClass(cls):
        rmtree(cls.workdir)

    def expect_line(self, fp, exp):
        for line in fp:
            print((line, exp))
            if line == exp:
                break
        else:
            self.fail()

    def expect_line_starting(self, gdb_pounce, gdb_args, exe):
        self.expect_line(
            gdb_pounce.stderr,
            f"Starting gdb -p {exe.pid} {GDB_ARGS} {gdb_args}...\n".encode(),
        )

    def expect_skip_non_matching(self, gdb_pounce, exe):
        self.expect_line(
            gdb_pounce.stderr,
            f"Skipping non-matching pid {exe.pid}...\n".encode(),
        )

    @contextmanager
    def popen_gdb_pounce(self, args):
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        gdb_pounce = Popen([self.gdb_pounce] + args, stderr=PIPE, env=env)
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
    def popen_hello(self, args):
        exe = Popen([self.hello] + args, stdout=PIPE)
        try:
            yield exe
        finally:
            try:
                self.assertEqual(HELLO_WORLD, exe.stdout.read())
            finally:
                self.assertEqual(0, exe.wait())
                exe.stdout.close()

    def test_collision(self):
        exe_path = os.path.join(self.workdir, "A" * TASK_COMM_LEN)
        copy(self.hello, exe_path)
        try:
            with self.popen_gdb_pounce(["A" * (TASK_COMM_LEN - 1)]) as gdb_pounce:
                exe = Popen([exe_path], stdout=PIPE)
                self.expect_skip_non_matching(gdb_pounce, exe)
                try:
                    self.assertEqual(HELLO_WORLD, exe.stdout.read())
                finally:
                    self.assertEqual(0, exe.wait())
                    exe.stdout.close()
        finally:
            os.unlink(exe_path)

    def test_matching_argv(self):
        gdb_args = ["-nx", "-batch", "-ex", "c", "-ex", "q"]
        gdb_args_str = "-nx -batch -ex c -ex q"
        with self.popen_gdb_pounce(gdb_args + ["hello", "bar"]) as gdb_pounce:
            with self.popen_hello(["foo", "bar", "baz"]) as exe:
                self.expect_line_starting(gdb_pounce, gdb_args_str, exe)
            self.expect_line(gdb_pounce.stderr, b"GDB exited.\n")

    def test_non_matching_argv(self):
        with self.popen_gdb_pounce(["hello", "quux"]) as gdb_pounce:
            with self.popen_hello(["foo", "bar", "baz"]) as exe:
                self.expect_skip_non_matching(gdb_pounce, exe)

    def test_matching_uid(self):
        gdb_args = ["-nx", "-batch", "-ex", "c", "-ex", "q"]
        gdb_args_str = "-nx -batch -ex c -ex q"
        with self.popen_gdb_pounce(
            [f"--uid={getpwuid(os.getuid())[0]}"] + gdb_args + ["hello"]
        ) as gdb_pounce:
            with self.popen_hello([]) as exe:
                self.expect_line_starting(gdb_pounce, gdb_args_str, exe)
            self.expect_line(gdb_pounce.stderr, b"GDB exited.\n")

    def test_non_matching_uid(self):
        with self.popen_gdb_pounce(
            ["--uid", str(os.getuid() + 1), "hello"]
        ) as gdb_pounce:
            with self.popen_hello([]) as exe:
                self.expect_skip_non_matching(gdb_pounce, exe)


if __name__ == "__main__":
    main()
