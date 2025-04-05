import yaml
import sys
import os
import random
import csv
from datetime import timedelta
from collections import defaultdict
from tqdm import tqdm
import time
import logging
import click
from typing import Any, Literal

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fit.injector import Injector
from fit.elf import ELF
from fit.stencil import Stencil
from fit.distribution import Fixed
from fit import logger

log = logger.get()
# log.setLevel(logging.DEBUG)


def timed_progress_bar(obj, duration=None):
    """Mostra una barra di avanzamento basata sul tempo di esecuzione di una funzione
    o su una stima per oggetti non callable.

    - Se obj è una funzione, misura il tempo reale di esecuzione.
    - Se obj è un oggetto non callable, simula un'attesa proporzionale alla sua 'dimensione'.
    """

    # Se obj è callable (una funzione), misuriamo il tempo reale
    if callable(obj):
        start = time.time()
        obj()  # Esegui la funzione
        duration = time.time() - start  # Calcola il tempo effettivo
    else:
        # Se obj NON è callable, stimiamo una durata fittizia
        if duration is None:
            duration = len(str(obj))  # Tempo basato sulla lunghezza dell'oggetto

        start = time.time()
        with tqdm(
            total=duration, desc="Esecuzione", bar_format="{l_bar}{bar} {n_fmt}/{total_fmt} sec"
        ) as pbar:
            while (elapsed := time.time() - start) < duration:
                pbar.update(elapsed - pbar.n)
                time.sleep(0.1)
            pbar.update(duration - pbar.n)  # Completa la barra


def click_option(*args: Any, **kwargs: Any) -> Any:
    if "show_default" not in kwargs:
        kwargs.update({"show_default": True})
    return click.option(*args, **kwargs)


@click.command()
@click_option(
    "-c",
    "--config-file",
    required=True,
    type=click.Path(exists=True, resolve_path=True, dir_okay=False),
    help="The path to the .yml configuration",
)
@click_option(
    "-r",
    "--remote",
    type=str,
    default=None,
    help="Override of the remote",
)
@click_option(
    "--log-level",
    default="info",
    type=click.Choice(
        ["info", "warning", "error", "debug"],
        case_sensitive=False,
    ),
)
def main(
    config_file: str,
    remote: str | None,
    log_level: Literal["info", "warning", "error", "debug"],
):
    log.setLevel(str(log_level).upper())

    print(f"**********************\n" f"* READ CONFIGURATION *\n" f"**********************\n")
    # Configuration file

    # Configuration data reads from yaml
    with open(config_file, "r") as yml_file:
        config = yaml.load(yml_file, Loader=yaml.FullLoader)

    # Injector data reads from CSV
    injector_data = defaultdict(lambda: defaultdict(dict))

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

    # Executable
    executable = config["configuration"]["executable"]

    if remote is None:
        remote = (
            "localhost:1234"
            if not config["configuration"]["gdb"]["remote"]
            else config["configuration"]["gdb"]["remote"]
        )

    inj = Injector(
        bin=executable,
        gdb_path=config["configuration"]["gdb"]["gdb_path"],
        remote=remote,
        embedded=config["configuration"]["gdb"]["embedded"],
        board=config["configuration"]["gdb"]["board"],
    )

    # Variables to inject
    injector_variables = []
    # Registers to inject
    injector_registers = []
    # Memories to inject
    injector_memories = []

    for element in injector_data.keys():
        if element in inj.regs.registers:
            injector_registers.append(element)
        elif element.startswith("0x"):
            injector_memories.append(element)
        else:
            injector_variables.append(element)

    print(f"\n\n\n" f"**************\n" f"* GOLDEN RUN *\n" f"**************\n")
    """
    Set-up
    """
    inj.reset()
    inj.set_result_condition(config["configuration"]["golden_result_condition"])
    inj.run()

    """
    Golden run
    """
    golden_run = {
        **{variable: inj.memory[variable] for variable in injector_variables},
        **{register: inj.regs[register] for register in injector_registers},
        **{memory: inj.memory[memory] for memory in injector_memories},
    }
    inj.add_run(golden_run, True)

    print(f"\n\n\n" f"*****************\n" f"* INJECTED RUNS *\n" f"*****************\n" f"\n")
    """
    Runs
    """
    runs = []
    for i in range(config["configuration"]["number_of_runs"]):
        print(f"!! {i + 1}")
        """
        Setup procedure
        """
        inj.reset()
        inj.set_result_condition(config["configuration"]["golden_result_condition"])
        for condition in config["configuration"]["result_condition"]:
            inj.set_result_condition(condition)

        def injection_function(inj: Injector) -> None:
            """
            Function that executes the injection.

            :param inj: the injection.
            """

            def choose_random_key(dictionary):
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
            gen = Stencil(patterns=values, pattern_distribution=Fixed(distribution))

            if where in injector_variables or where in injector_memories:
                actual: slice[int, int, int] | int | str = 0
                if ":" in where:
                    start, end = where.split(":")
                    start = int(start, 16)
                    end = int(end, 16)

                    actual = slice(start, end, 1)
                elif where.startswith("0x"):
                    actual = int(where, 16)
                elif isinstance(where, str):
                    actual = where
                else:
                    log.critical(f"Unreachable")

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
            timeout=timedelta(
                seconds=random.randint(
                    int(config["configuration"]["timeout_interval"]["min"]),
                    int(config["configuration"]["timeout_interval"]["max"]),
                )
            ),
            injection_delay=timedelta(
                seconds=random.randint(
                    int(config["configuration"]["injection_delay"]["min"]),
                    int(config["configuration"]["injection_delay"]["max"]),
                )
            ),
            inject_func=injection_function,
        )

        print(f"{' ' * (len(str(abs(i + 1))) + len("!! "))}RUN RESULT {result}\n")
        inj.result_run.append(result)

        """
        Look at the memory and registers
        """
        inj.add_run(
            {
                **{variable: inj.memory[variable] for variable in injector_variables},
                **{register: inj.regs[register] for register in injector_registers},
                **{memory: inj.memory[memory] for memory in injector_memories},
            }
        )

    print(f"\n\n\n" f"***************\n" f"* SAVE RESULT *\n" f"***************\n")
    """
    Save the data in CSV file
    """
    inj.save(config["configuration"]["experiment_name"])
    inj.close()


if __name__ == "__main__":
    main()
