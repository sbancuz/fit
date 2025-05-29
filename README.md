# Fault Injection Toolkit

This project is a fault injector for embedded systems for the course Advanced Operating Systems.

## Install

```bash
$ poetry install
```

Currently supported embedded architectures:
 - STM32 <- Use [st-util](https://github.com/stlink-org/stlink) for `gdbserver`

> [!Note]
> It works even with non-embedded targets, remotely (using `gdbserver`) or locally. For embedded targets, only remotely!

## Quickstart

```bash
$ cc -ggdb -O0 -no-pie -o example example.c
$ fit -c example_config.yml
```

It also provides a library to create custom injectors by importing the module `fit`.
