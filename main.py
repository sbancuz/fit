import csv
import random
from collections import defaultdict
from datetime import timedelta
from typing import Any, DefaultDict, Literal

import click
import yaml
from tqdm import tqdm

from fit import logger
from fit.distribution import Fixed, Uniform
from fit.fitlib import gdb_injector
from fit.injector import Injector
from fit.interfaces.implementations import Implementation
from fit.stencil import Stencil

log = logger.get()


def format_memory_addr(s: slice[int, int, int] | int) -> str:
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


@click.command()
@click.option(
    "-c",
    "--config-file",
    required=True,
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
def main(
    config_file: str,
    remote: str | None,
    log_level: Literal["info", "warning", "error", "debug"],
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

    injector_data: DefaultDict[str, DefaultDict[str, dict[Any, Any]]] = defaultdict(
        lambda: defaultdict(dict)
    )

    with open(config["injector"], mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            where = row["where"]
            operation = row["operation"]
            entry = {
                "value": int(row["value"]),
                "value_probability": float(row["value_probability"]),
            }

            if "operation_probability" not in injector_data[where][operation]:
                injector_data[where][operation]["operation_probability"] = float(
                    row["operation_probability"]
                )
                injector_data[where][operation]["values"] = []

            injector_data[where][operation]["values"].append(entry)

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

    injector_variables = []
    injector_registers = []
    injector_memories = []

    for element in injector_data.keys():
        if element in inj.regs.registers:
            injector_registers.append(element)
        elif element.startswith("0x"):
            injector_memories.append(to_mem_val(element))

        else:
            injector_variables.append(element)

    log.info("Starting golden run")
    inj.reset()
    inj.set_result_condition(golden_result_condition)

    result = inj.run()

    golden_run = {
        "result": result,
        **{variable: inj.memory[variable] for variable in injector_variables},
        **{register: inj.regs[register] for register in injector_registers},
        **{format_memory_addr(memory): inj.memory[memory] for memory in injector_memories},
    }
    log.info(golden_run)
    inj.add_run(golden_run, True)

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

            def choose_random_key(dictionary: dict[Any, Any]) -> Any:
                """
                Function that chooses a random key given a distribution.

                :param dictionary: the dictionary that contains the distribution.
                :return: the interesting key.
                """

                return random.choices(list(dictionary.keys()), list(dictionary.values()))[0]

            # Where, Operation - Operation_probability dictionary
            combined_dict = {}
            for where, operations in injector_data.items():
                for operation, details in operations.items():
                    key = (where, operation)
                    combined_dict[key] = details["operation_probability"]

            # Where - Operation dictionary
            where_operation = choose_random_key(combined_dict)

            # Where to do injection
            where = where_operation[0]
            # Which operation executes to do injection
            operation = where_operation[1]
            # Which value use during injection
            values = [
                int(v["value"])
                for v in injector_data[where_operation[0]][where_operation[1]]["values"]
            ]
            distribution = [
                float(v["value_probability"])
                for v in injector_data[where_operation[0]][where_operation[1]]["values"]
            ]
            gen = Stencil(
                patterns=values,
                pattern_distribution=Fixed(distribution),
                word_size=inj.binary.bits // 8,
            )

            if where in injector_variables or to_mem_val(where) in injector_memories:
                actual = to_mem_val(where)
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
        log.info(str(run))

    inj.save(experiment_name)
    inj.close()


if __name__ == "__main__":
    main()
