CC := gcc
CFLAGS = -O0 -ggdb -no-pie
SRC_DIRS := testbench

SRC_FILES := $(wildcard $(addsuffix /*.c, $(SRC_DIRS)))
TARGETS := $(patsubst %, out/%, $(SRC_FILES))

all: $(TARGETS)

out/%: % 
	@mkdir -p $(@D)
	-$(CC) $(CFLAGS) -o $@ $<

.PHONY: all clean .FORCE

clean:
	rm -rf out/*
