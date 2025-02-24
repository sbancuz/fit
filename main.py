from datetime import timedelta
import subprocess

from fit.injector import Injector

def start_server():
   subprocess.call(['gdbserver', 'localhost:1234', './foo'])

if __name__ == "__main__":
   # start_server()

   inj = Injector(
      bin='foo',
      # gdb_path='arm-none-eabi-gdb',
      gdb_path='gdb',
      remote='localhost:1234',
      embeded=False,
   )

   for i in range(1):
      """
      Setup procedure
      """
      inj.reset()
      inj.set_timeout(timedelta(seconds=1))
      inj.set_result_condition('main', lambda _ : print('SIGINT'))

      ## This works, it just doesn't point to valid memory so it's commented
      # print(inj.memory[0x20000000:0x20000004])
      print(inj.memory['i'])
      inj.memory['i'] |= 15
      print(inj.memory['i'])
      ## This works, it just doesn't point to valid memory so it's commented
      # inj.memory[0x20000000:0x20000004] = [0x1234, 0x5678]

      ### This works, it just doesn't point to valid memory so it's commented
      ## Put our own random stuff
      # inj.memory[0x20000000 + random.randint(0, 10)] |= 0b000010000
      inj.regs['rax'] = 0x20000000

      """
      Experiment
      """
      print(inj.run())

      """
      Look at the memory and registers
      """
      ## This works, it just doesn't point to valid memory so it's commented
      # print(inj.memory[0x20000000])
      print(inj.regs['rax'])

   inj.close()
