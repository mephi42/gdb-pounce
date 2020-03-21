# gdb-pounce

Attach to a process precisely after a successful `execve()` / `execveat()`.

# Usage

```
sudo gdb-pounce COMM
```

# Prerequisites

* [bcc](https://github.com/iovisor/bcc) `>= 0.11.0`
* [gdb](https://www.gnu.org/software/gdb/)
* [linux kernel](https://www.kernel.org/) `>= 5.3`
* [python3](https://www.python.org/) `>= 3.7`

# pounce?

`gdb-pounce` lies in wait for its victim process. The very moment the process
appears, `gdb-pounce` pounces at it and seizes it, leaving it no chance to
react.
