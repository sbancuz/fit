# Fault Injection Toolbox

This project is a fault injector for embedded systems for the course Advanced Operating Systems.

## Install

```sh
$ poetry install
```

Currently supported architectures:
 - STM32 <- Use `st-ultils` for `gdbserver`

## Quickstart

```sh
$ cc -ggdb -O0 -o example example.c
$ gdbserver localhost:1234 example &
$ fit -c example_config.yml
$ pkill gdbserver
```

It also provides a library to create custom injectors by importing the module `fit`.
