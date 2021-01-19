.. image:: https://img.shields.io/pypi/v/gdb-pounce
   :target: https://pypi.python.org/pypi/gdb-pounce
   :alt: PyPI

gdb-pounce
==========

Attach to a process precisely after a successful ``execve()`` / ``execveat()``.

Usage
=====

.. code-block::

   sudo ./gdb-pounce COMM

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
