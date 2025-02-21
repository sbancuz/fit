import os
from datetime import timedelta

from fit.injector import Injector
import random

def start_server():
   os.system('st-util -p 1234')

if __name__ == "__main__":
   start_server()

   inj = Injector(
      elf='file.elf',
      gdb_path='arm-none-eabi-gdb',
      remote='localhost:1234',
   )

   for i in range(10):
      """
      Setup procedure
      """
      inj.reset()
      inj.set_timeout(timedelta(seconds=1))
      inj.set_result_condition('handler_1', lambda: print('SIGINT'))

      inj.memory[0x20000000] = 0x1234
      inj.memory['var'] |= 0b000010000
      inj.memory[0x20000000:0x20000004] = [0x1234, 0x5678]
      ## Put our own random stuff
      inj.memory[0x20000000 + random.randint(0, 10)] |= 0b000010000
      inj.regs.r0 = 0x20000000

      """
      Experiment
      """
      inj.run()

      """
      Look at the memory and registers
      """ 
      print(inj.memory[0x20000000])
      print(inj.regs.r0)
