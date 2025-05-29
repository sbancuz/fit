
#include <stdio.h>
#include <unistd.h>

static int i = 10, a = 50;

void foo() { printf("Changed value of i! %d\n", i); }
void win() { printf("End\n"); }

int main() {
  while (1) {
    i = 10;
    sleep(5);

    if (i != 10)
      foo();

    sleep(5);

    win();
  }
  return 0;
}
