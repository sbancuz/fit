import csv
import json
import random
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any, DefaultDict, Literal

import click
import pandas as pd
import yaml
from tqdm import tqdm

from fit import logger
from fit.csv import import_from_csv
from fit.distribution import Fixed, Uniform
from fit.elf import ELF
from fit.fitlib import gdb_injector
from fit.injector import Injector
from fit.interfaces.implementations import Implementation
from fit.stencil import Stencil

log = logger.get()


def format_memory_addr(s: slice | int) -> str:
    if not isinstance(s, slice):
        return f"0x{s:x}"

    start = s.start if s.start is not None else 0
    stop = s.stop if s.stop is not None else 0
    return f"0x{start:x}:0x{stop:x}"


def to_mem_val(element: str) -> slice | int:
    if ":" in element:
        start, end = element.split(":")
        return slice(int(start, 16), int(end, 16))
    else:
        return int(element, 16)


"""
   contare occorrenze
"""


def format_memory_range(golden: str, run: str, format: bool = True) -> str:
    golden = json.loads(golden)
    run = json.loads(run)

    gvals = [int(v) for v in golden]
    rvals = [int(v) for v in run]

    diff = [gold - r for gold, r in zip(gvals, rvals)]

    if len(diff) == 1:
        if diff[0] != 0:
            return "\033[31m" + hex(rvals[0])[2:] + "\033[0m..."
        else:
            return hex(rvals[0])[2:]

    res = hex(rvals[0])[2:]

    count = -1
    for i, v in enumerate(diff):
        if v == 0:
            if count == 0:
                if format:
                    res += "\033[0m..."
                else:
                    res += "..."
            count += 1

        else:
            if count == -1:
                count = 0

                res = ""

            if count > 0:
                res += f"[{i}]..."
                count = 0

            if format:
                res += "\033[31m"

            res += hex(rvals[i])[2:]

    if count == 1:
        res = res[:-3]
        res += hex(rvals[-1])[2:]
    elif count > 1:
        res += f"[{count - 1}]...{hex(rvals[-1])[2:]}"

    return res + "\033[0m"


def print_report(config: dict[str, Any]) -> None:
    """
    Function that prints a report of the experiment.

    :param config: the configuration dictionary.
    """
    exp_name = config["configuration"]["experiment_name"]
    golden_result_condition = config["configuration"]["golden_result_condition"]
    result_conditions = config["configuration"]["result_condition"]

    elf = ELF(config["configuration"]["executable"])
    ## Keep these in line
    runs = import_from_csv(exp_name + ".csv")
    golden = import_from_csv(exp_name + "_golden.csv")

    count_different_from_golden = defaultdict(Counter)
    for key in runs:
        count_different_from_golden[key] = Counter(runs[key])

    if "Timeout" not in count_different_from_golden["result"]:
        count_different_from_golden["result"]["Timeout"] = 0

    if golden_result_condition not in count_different_from_golden["result"]:
        count_different_from_golden["result"][golden_result_condition] = 0

    for condition in result_conditions:
        if condition not in count_different_from_golden["result"]:
            count_different_from_golden["result"][condition] = 0

    for key in golden:
        if key != "result":
            if golden[key][0] not in count_different_from_golden[key]:
                count_different_from_golden[key][golden[key][0]] = 0

    print(f"Injection Result:")
    for key in count_different_from_golden:
        print(f"{key}:")
        for i in count_different_from_golden[key].keys():
            if key.startswith("0x") or (
                elf.symbols[key] is not None and elf.symbols[key].size > elf.bits // 8
            ):
                pr = format_memory_range(golden[key][0], i)
            else:
                pr = f"{i}"

            if i == golden[key][0]:
                pr = pr.replace("\033[31m", "")
                pr = pr.replace("\033[0m", "")
                print(
                    f" - \033[33m{pr}: {count_different_from_golden[key][i]} / {len(runs[key])}\033[0m"
                )
            else:
                print(f" - {pr}: {count_different_from_golden[key][i]} / {len(runs[key])}")
        print()

    experiment_df = pd.read_csv(exp_name + ".csv")
    experiment_df_filtered = experiment_df[
        experiment_df["result"] != golden["result"][0]
    ].drop_duplicates()

    print(f"\n\nRuns that differ from golden:")
    for i, row in experiment_df_filtered.iterrows():
        print(" - ", end="")
        for col in experiment_df_filtered.columns:
            val = str(row[col])
            if col != "result" and val != str(golden[col][0]):
                print(f"\033[33m{val}\033[0m", end=" ")
            else:
                print(val, end=" ")
        print()


@click.command()
@click.option(
    "-c",
    "--config-file",
    required=False,
    type=click.Path(exists=True, resolve_path=True, dir_okay=False),
    help="The path to the .yml configuration",
)
@click.option(
    "-r",
    "--remote",
    type=str,
    default=None,
    help="Override of the remote",
)
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(
        ["info", "warning", "error", "debug"],
        case_sensitive=False,
    ),
    show_default=True,
)
@click.option(
    "--report",
    flag_value=True,
    default=False,
    help="Report stats for an experiment, the runs are read from the config file",
)
def main(
    config_file: str,
    remote: str | None,
    log_level: Literal["info", "warning", "error", "debug"],
    report: bool,
) -> None:
    """
    Main function that runs the injection process based on the configuration file and options provided.

    :param config_file: the path to the YAML configuration file.
    :param remote: the remote target of GDB.
    :param log_level: the logging level.
    """

    log.setLevel(str(log_level).upper())

    with open(config_file, "r") as yml_file:
        config = yaml.load(yml_file, Loader=yaml.FullLoader)

    if config.get("configuration") is None:
        log.critical(
            "Configuration field not specified, please look at the example for a correct configuration file"
        )

    if (executable := config["configuration"].get("executable")) is None:
        log.critical("Executable not set")
        return

    if (golden_result_condition := config["configuration"].get("golden_result_condition")) is None:
        log.critical("Golden result condition not set")
        return

    if (result_conditions := config["configuration"].get("result_condition")) is None:
        log.critical("Result condition not set")
        return

    if (number_of_runs := config["configuration"].get("number_of_runs")) is None:
        log.critical("Number of runs not set")
        return

    if (timeout := config["configuration"].get("timeout")) is None:
        log.critical("Timeout is not set")
        return

    if (injection_delay := config["configuration"].get("injection_delay")) is None:
        log.critical("Injection delay not set")
        return

    if (inj_min := injection_delay.get("min")) is None:
        log.critical("Injection delay min not set")
        return

    if (inj_max := injection_delay.get("max")) is None:
        log.critical("Injection delay max not set")
        return

    if (experiment_name := config["configuration"].get("experiment_name")) is None:
        log.critical("Experiment name not set")
        return

    if report:
        print_report(config)

        return

    if config["configuration"]["gdb"] is not None:
        if (gdb_path := config["configuration"]["gdb"].get("gdb_path", None)) is None:
            log.critical("GDB path not set")
            return

        if (embedded := config["configuration"]["gdb"].get("embedded", None)) is None:
            log.warning("Embedded not set, defaulting to False")
            embedded = False

        board_family = config["configuration"]["gdb"].get("board_family", "UNKNOWN")

        if remote is None:
            if "remote" not in config["configuration"]["gdb"]:
                log.info("Running locally...")
            else:
                remote = config["configuration"]["gdb"]["remote"]
                log.info(f"Running remotely on {remote}...")

        log.info("Configuration read")
        inj = gdb_injector(
            bin=executable,
            remote=remote,
            gdb_path=gdb_path,
            embedded=embedded,
            board_family=board_family,
        )
    else:
        log.error(f"Unrecognized injector backend, list of supported backends:")
        for impl in Implementation:
            log.error(impl)

        log.critical("Please select a correct backend")
        return

    if (injector := config.get("injector")) is None:
        log.critical("Injector path is not specified")
        return

    # read the injector csv
    injector_csv = pd.read_csv(injector)

    # divide the where data into variables, registers, and memory
    injector_variables = []
    injector_registers = []
    injector_memories = []

    for element in injector_csv["where"].unique().tolist():
        if element in inj.regs.registers:
            injector_registers.append(element)
        elif element.startswith("0x"):
            injector_memories.append(to_mem_val(element))
        else:
            injector_variables.append(element)

    # Start Golden Run
    log.info("Starting golden run")
    inj.reset()
    inj.set_result_condition(golden_result_condition)
    for condition in result_conditions:
        inj.set_result_condition(condition)

    result = inj.run()
    if result in result_conditions:
        log.error(f"Golden run didn't reach end: got {result} expected: {golden_result_condition}")

    golden_run = {
        "result": result,
        **{variable: inj.memory[variable] for variable in injector_variables},
        **{register: inj.regs[register] for register in injector_registers},
        **{format_memory_addr(memory): inj.memory[memory] for memory in injector_memories},
    }
    # log.info(golden_run)
    inj.add_run(golden_run, True)

    # Start Runs
    log.info("Starting runs...")
    for h in log.handlers[:]:
        log.removeHandler(h)
    log.addHandler(logger.TqdmLoggingHandler())

    for i in tqdm(range(number_of_runs), desc="Runs", unit="run"):
        log.info(f"Run: {i + 1}/{number_of_runs}")
        """
        Setup procedure
        """
        inj.reset()
        inj.set_result_condition(golden_result_condition)
        for condition in result_conditions:
            inj.set_result_condition(condition)

        def injection_function(inj: Injector) -> None:
            """
            Function that executes the injection.

            :param inj: the injection.
            """

            # where, operation, operation_probability
            where_operation_probability = list(
                injector_csv[["where", "operation", "operation_probability"]]
                .drop_duplicates()
                .itertuples(index=False, name=None)
            )
            choices = [(w, op, p) for w, op, p in where_operation_probability]
            weights = [p for w, op, p in where_operation_probability]
            where_operation_selected = random.choices(choices, weights=weights, k=1)[0]

            selected_where_operation_probability_df = injector_csv[
                (injector_csv["where"] == where_operation_selected[0])
                & (injector_csv["operation"] == where_operation_selected[1])
                & (injector_csv["operation_probability"] == where_operation_selected[2])
            ]

            # Where to do injection
            where = where_operation_selected[0]
            # Which operation executes to do injection
            operation = where_operation_selected[1]
            # Which value uses during injection
            values = selected_where_operation_probability_df["value"].tolist()
            # Which distribution uses during injection
            distribution = selected_where_operation_probability_df["value_probability"].tolist()

            gen = Stencil(
                patterns=values,
                pattern_distribution=Fixed(distribution),
                word_size=inj.binary.bits // 8,
            )

            if where in injector_variables or to_mem_val(where) in injector_memories:
                actual: slice | str | int = where
                if where not in injector_variables:
                    actual = to_mem_val(where)

                if isinstance(actual, str):
                    sym = inj.binary.symbols[where]
                    gen.offset_distribution = Uniform(
                        0, ((sym.value + sym.size) - sym.value) * 8, granularity=inj.binary.bits
                    )

                if isinstance(actual, slice):
                    gen.offset_distribution = Uniform(
                        0, (actual.stop - actual.start) * 8, granularity=inj.binary.bits
                    )

                if operation == "xor":
                    inj.memory[actual] ^= gen.random()
                elif operation == "and":
                    inj.memory[actual] &= gen.random()
                elif operation == "or":
                    inj.memory[actual] |= gen.random()
                elif operation == "zero":
                    inj.memory[actual] = 0
                elif operation == "value":
                    inj.memory[actual] = gen.random()

            elif where in injector_registers:
                if operation == "xor":
                    inj.regs[where] ^= gen.random()
                elif operation == "and":
                    inj.regs[where] &= gen.random()
                elif operation == "or":
                    inj.regs[where] |= gen.random()
                elif operation == "zero":
                    inj.regs[where] = 0
                elif operation == "value":
                    inj.regs[where] = gen.random()
            else:
                log.critical("Invalid target for injection")

        result = inj.run(
            timeout=timedelta(milliseconds=timeout),
            injection_delay=timedelta(milliseconds=random.randint(inj_min, inj_max)),
            inject_func=injection_function,
        )

        log.info(result)

        """
        Look at the memory and registers
        """
        run = {
            "result": result,
            **{variable: inj.memory[variable] for variable in injector_variables},
            **{register: inj.regs[register] for register in injector_registers},
            **{format_memory_addr(memory): inj.memory[memory] for memory in injector_memories},
        }
        inj.add_run(run)
        # log.info(str(run))

    inj.save(experiment_name)
    inj.close()


if __name__ == "__main__":
    main()
