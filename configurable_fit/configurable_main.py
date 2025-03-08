import yaml
import sys
import os
import random
from datetime import timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fit.injector import Injector
from fit.elf import ELF




if __name__ == "__main__":
    #Configuration file
    config_file = "config.yml"


    if len(sys.argv) == 2:
        config_file = sys.argv[1]


    with open(config_file, "r") as ymlfile:
        config = yaml.load(ymlfile, Loader=yaml.FullLoader)


    #Executable
    executable = config["configuration"]["executable"]

    #Injector
    inj = Injector(
        bin=executable,
        gdb_path=config["configuration"]["gdb_path"],
        remote=config["configuration"]["remote"],
        embedded=config["configuration"]["embedded"],
    )

    #ELF
    elf = ELF(executable)
    #Address
    address = elf.symbols[executable].value


    inj.reset()
    inj.set_result_condition(executable, lambda _ : print('hit a breakpoint, this result is also provided as the return value of inj.run()'))
    inj.run()


    #Golden run
    golden_run = {
        **{variable["name"]: inj.memory[variable["name"]] for variable in config["where_I_want_to_do_injection"]["variable"]},
        **{register: inj.regs[register] for register in config["where_I_want_to_do_injection"]["register"]},
        **{memory : inj.memory[memory] for memory in config["where_I_want_to_do_injection"]["memory"]},
    }
    inj.save(config["configuration"]["experiment_name"])
    inj.add_run(golden_run, True)


    #Runs
    runs = []
    for i in range(config["configuration"]["number_of_runs"]):
        """
        Setup procedure
        """
        inj.reset()
        inj.set_result_condition(executable, lambda _ : print('hit a breakpoint, this result is also provided as the return value of inj.run()'))


        """
        Experiment
        """
        def injection_function_variable(inj: Injector) -> None:
            def choose_variable(probability_dictonary):
                return random.choices(list(probability_dictonary.keys()), weights=probability_dictonary.values(), k=1)[0]

            inj.memory[choose_variable(config["distribution_and_probability_of_where_to_do_injection"]["variable"])] = 0x12


        print(inj.run(
            timeout=timedelta(seconds=random.randint(config["configuration"]["timeout_interval"]["min"], config["configuration"]["timeout_interval"]["max"])),
            injection_delay=timedelta(seconds=random.randint(config["configuration"]["injection_delay"]["min"], config["configuration"]["injection_delay"]["max"])),
            inject_func=injection_function_variable,
        ))

        """
        Look at the memory and registers
        """
        runs.append({
            **{variable["name"]: inj.memory[variable["name"]] for variable in config["where_I_want_to_do_injection"]["variable"]},
            **{register: inj.regs[register] for register in config["where_I_want_to_do_injection"]["register"]},
            **{memory: inj.memory[memory] for memory in config["where_I_want_to_do_injection"]["memory"]},
        })

    inj.close()