import yaml
import sys
import os
import random
import csv
from datetime import timedelta
from collections import defaultdict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fit.injector import Injector
from fit.elf import ELF
from fit.stencil import Stencil
from fit.distribution import Fixed
from fit import logger

log = logger.get(__name__)


if __name__ == "__main__":
    # Configuration file
    config_file = "config.yml"

    if len(sys.argv) == 2:
        config_file = sys.argv[1]

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
    # ELF
    elf = ELF(executable)

    # Injector
    inj = Injector(
        bin=executable,
        gdb_path=config["configuration"]["gdb_path"],
        remote="localhost:1234" if config["configuration"]["remote"] else None,
        embedded=config["configuration"]["embedded"],
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

    print("GOLDEN")
    """
    Set-up
    """
    inj.reset()
    inj.set_result_condition("end")
    inj.run()

    """
    Golden run
    """
    # print(inj.memory["test"])
    golden_run = {
        **{variable: inj.memory[variable] for variable in injector_variables},
        **{register: inj.regs[register] for register in injector_registers},
        **{memory: inj.memory[memory] for memory in injector_memories},
    }
    print(list(golden_run.keys())[0])
    inj.add_run(golden_run, True)

    """
    Runs
    """
    runs = []
    for i in range(config["configuration"]["number_of_runs"]):
        """
        Setup procedure
        """
        inj.reset()
        inj.set_result_condition("end")
        inj.set_result_condition("foo")

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
                    inj.memory[where] ^= gen.random()
                elif operation == "and":
                    inj.memory[where] &= gen.random()
                elif operation == "or":
                    inj.memory[where] |= gen.random()
                elif operation == "zero":
                    inj.memory[where] = 0
                elif operation == "value":
                    inj.memory[where] = gen.random()
            else:
                log.critical("Invalid target for injection")

        ## TODO: Tenere traccia degli eventi lanciati
        print(
            inj.run(
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
        )

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

    """
    Save the data in CSV file
    """
    inj.save(config["configuration"]["experiment_name"])
    inj.close()
