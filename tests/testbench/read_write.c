
#include <stdio.h>
#include <unistd.h>

static unsigned int vmax1 = -1;
static unsigned int vmax2 = -1;
static unsigned int vmax3 = -1;
static unsigned int vmax4 = -1;
static unsigned int vmax5 = -1;
static unsigned int vmax6 = -1;
static unsigned int vmax7 = -1;
static unsigned int vmax8 = -1;

static unsigned int vzero1 = 0;
static unsigned int vzero2 = 0;
static unsigned int vzero3 = 0;
static unsigned int vzero4 = 0;
static unsigned int vzero5 = 0;
static unsigned int vzero6 = 0;
static unsigned int vzero7 = 0;
static unsigned int vzero8 = 0;

void stop() { printf("End\n"); }

int main() {
  while (1) {
    stop();
  }
  return 0;
}
