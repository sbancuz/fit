import yaml
import sys
import os
import random
import csv
from datetime import timedelta
from collections import defaultdict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fit.injector import Injector
from fit.elf import ELF
from fit.stencil import Stencil
from fit.distribution import Fixed


def xor_function(a, b) -> int:
    """
    Function that executes the xor operation.

    :param a: the first parameter.
    :param b: the second parameter.

    :return: the xor value.
    """

    return a ^ b


def and_function(a, b) -> int:
    """
    Function that executes the and operation.

    :param a: the first parameter.
    :param b: the second parameter.

    :return: the and value.
    """

    return a & b


def or_function(a, b) -> int:
    """
    Function that executes the or operation.

    :param a: the first parameter.
    :param b: the second parameter.

    :return: the or value.
    """


    return a | b


def zeroing_function() -> int:
    """
    Function that executes the zeroing operation.

    :return: the zero value.
    """

    return 0


def value_function(a) -> int:
    """
    Function that executes the value operation.

    :param a: the value.

    :return: the value.
    """

    return a


if __name__ == "__main__":
    #Configuration file
    config_file = "config.yml"


    if len(sys.argv) == 2:
        config_file = sys.argv[1]


    #Configuration data reads from yaml
    with open(config_file, "r") as yml_file:
        config = yaml.load(yml_file, Loader=yaml.FullLoader)


    #Injector data reads from CSV
    injector_data = defaultdict(lambda: defaultdict(dict))

    with open(config["injector"], mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            where = row["where"]
            operation = row["operation"]
            entry = {
                "value": int(row["value"]),
                "value_probability": float(row["value_probability"])
            }

            if "operation_probability" not in injector_data[where][operation]:
                injector_data[where][operation]["operation_probability"] = float(row["operation_probability"])
                injector_data[where][operation]["values"] = []

            injector_data[where][operation]["values"].append(entry)


    #Executable
    executable = config["configuration"]["executable"]
    #ELF
    elf = ELF(executable)
    #Address
    address = elf.symbols[executable].value


    #Injector
    inj = Injector(
        bin=executable,
        gdb_path=config["configuration"]["gdb_path"],
        remote="localhost:1234" if config["configuration"]["remote"] else None,
        embedded=config["configuration"]["embedded"],
    )


    #Variables to inject
    injector_variables = []
    #Registers to inject
    injector_registers = []
    #Memories to inject
    injector_memories = []

    for element in injector_data.keys():
        if element in inj.regs.registers:
            injector_registers.append(element)
        elif element.startswith("0x"):
            injector_memories.append(element)
        else:
            injector_variables.append(element)


    """
    Set-up
    """
    inj.reset()
    inj.set_result_condition(executable)
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


    """
    Runs
    """
    runs = []
    for i in range(config["configuration"]["number_of_runs"]):
        """
        Setup procedure
        """
        inj.reset()
        inj.set_result_condition(executable, lambda _ : print('hit a breakpoint, this result is also provided as the return value of inj.run()'))


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


            #Where - Operation dictionary
            where_operation = choose_random_key(combined_dict)

            #Where to do injection
            where = where_operation[0]
            #Which operation executes to do injection
            operation = where_operation[1]
            #Which value use during injection
            value = choose_random_key({item["value"]: item["value_probability"] for item in injector_data[where_operation[0]][where_operation[1]]["values"]})


            def choose_how_to_make_injection(operation_to_compute: str, a: int, value: int) -> None | int:
                """
                Function that chooses the operation to execute.

                :param operation_to_compute: the operation to compute.
                :param a: the first value.
                :param value: the value specified by the user.
                :return:
                """

                if operation_to_compute == "xor":
                    return xor_function(a, value)
                elif operation_to_compute == "and":
                    return and_function(a, value)
                elif operation_to_compute == "or":
                    return or_function(a, value)
                elif operation_to_compute == "zero":
                    return zeroing_function()
                elif operation_to_compute == "value":
                    return value_function(value)
                else:
                    return None


            if where in injector_variables or where in injector_memories:
                inj.memory[where] = choose_how_to_make_injection(operation, inj.memory[where], value)
            elif where in injector_registers:
                inj.regs[where] = choose_how_to_make_injection(operation, inj.regs[where], value)
            else:
                sys.exit(1)


        print(inj.run(
            timeout=timedelta(seconds=random.randint(config["configuration"]["timeout_interval"]["min"], config["configuration"]["timeout_interval"]["max"])),
            injection_delay=timedelta(seconds=random.randint(config["configuration"]["injection_delay"]["min"], config["configuration"]["injection_delay"]["max"])),
            inject_func=injection_function,
        ))


        """
        Look at the memory and registers
        """
        runs.append({
            **{variable: inj.memory[variable] for variable in injector_variables},
            **{register: inj.regs[register] for register in injector_registers},
            **{memory: inj.memory[memory] for memory in injector_memories},
        })


    """
    Save the data in CSV file
    """
    inj.save(config["configuration"]["experiment_name"])
    inj.close()