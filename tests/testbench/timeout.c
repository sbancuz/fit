#include <stdio.h>
#include <unistd.h>

void stop() { printf("End\n"); }

int main() {
  while (1) {
    __asm__ __inline__("nop");
  }
  return 0;
}
