#!/usr/bin/env python3
import os
import signal
from shutil import copy, rmtree
from subprocess import PIPE, Popen, check_call
from tempfile import mkdtemp
from unittest import TestCase, main

TASK_COMM_LEN = 16
RUNNING = b"Running, press Ctrl+C to stop...\n"


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
            if line == exp:
                break
        else:
            self.fail()

    def test_collision(self):
        exe_path = os.path.join(self.workdir, "A" * TASK_COMM_LEN)
        copy(self.hello, exe_path)
        try:
            env = dict(os.environ)
            env["PYTHONUNBUFFERED"] = "1"
            gdb_pounce = Popen(
                [self.gdb_pounce, "A" * (TASK_COMM_LEN - 1)], stderr=PIPE, env=env
            )
            try:
                self.expect_line(gdb_pounce.stderr, RUNNING)
                exe = Popen([exe_path], stdout=PIPE)
                self.expect_line(
                    gdb_pounce.stderr,
                    f"Skipping non-matching pid {exe.pid}...\n".encode(),
                )
                try:
                    self.assertEqual(b"Hello, World!\n", exe.stdout.read())
                finally:
                    self.assertEqual(0, exe.wait())
                    exe.stdout.close()
                os.kill(gdb_pounce.pid, signal.SIGINT)
            finally:
                self.assertEqual(0, gdb_pounce.wait())
                gdb_pounce.stderr.close()
        finally:
            os.unlink(exe_path)


if __name__ == "__main__":
    main()
