#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv) {
  int do_fork = 0;
  for (int i = 0; i < argc; i++) {
    if (strcmp(argv[i], "--fork") == 0)
      do_fork = 1;
  }
  puts("Hello, World!");
  if (do_fork) {
    fflush(stdout);
    pid_t pid = fork();
    if (pid == -1)
      abort();
    if (pid == 0) {
      puts("Hello, Fork!");
      exit(0);
    }
    int wstatus;
    pid_t pid_again = waitpid(pid, &wstatus, 0);
    if (pid_again != pid)
      abort();
    if (wstatus != 0)
      abort();
  }
}
