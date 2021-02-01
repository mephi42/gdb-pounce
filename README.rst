.. image:: https://img.shields.io/pypi/v/gdb-pounce
   :target: https://pypi.python.org/pypi/gdb-pounce
   :alt: PyPI

gdb-pounce
==========

Wait until a process with a certain name starts and attach to it with ``gdb``.
While for many use cases

.. code-block::

    while ! pidof "$NAME"; do :; done; gdb -p "$(pidof "$NAME")"

is sufficient, ``gdb-pounce`` will stop right at the loader entry point, as if
the process was started under ``gdb`` in the first place.

Usage
=====

.. code-block::

   python3 -m pip install --upgrade --user gdb-pounce
   sudo env "PATH=$PATH" gdb-pounce [GDB OPTION]... [NAME]

When is this useful?
====================

When an interesting process (usually a part of some complex software) starts in
a non-trivial environment, for example:

- As a specific user.
- In a specific namespace.
- With additional environment variables.
- With additional file descriptors.
- While another process is in a specific state.

and we need to debug its initialization.

Prerequisites
=============

* `bcc <https://github.com/iovisor/bcc>`_ ``>= 0.11.0``
* `gdb <https://www.gnu.org/software/gdb/>`_
* `linux kernel <https://www.kernel.org/>`_ ``>= 5.3``
* `python3 <https://www.python.org/>`_ ``>= 3.7``

pounce?
=======

``gdb-pounce`` lies in wait for its victim process. The very moment the process
appears, ``gdb-pounce`` pounces at it and seizes it, leaving it no chance to
react.
