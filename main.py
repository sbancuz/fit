from datetime import timedelta

from fit.injector import Injector
from fit.elf import ELF

if __name__ == "__main__":
   inj = Injector(
      bin='foo',
      # gdb_path='arm-none-eabi-gdb',
      gdb_path='gdb',
      remote='localhost:1234',
      embeded=False,
   )

   elf = ELF('configurable_fit/foo')
   addr = elf.symbols['foo'].value

   inj.reset()
   inj.set_result_condition('foo', lambda _ : print('hit a breakpoint, this result is also provided as the return value of inj.run()'))

   inj.run()

   golden = {
      'i' : inj.memory['i'],
   }

   runs = []
   for i in range(1):
      """
      Setup procedure
      """
      inj.reset()
      inj.set_result_condition('foo', lambda _ : print('hit a breakpoint, this result is also provided as the return value of inj.run()'))

      # print(inj.memory[0x20000000:0x20000004]) ## This works, it just doesn't point to valid memory so it's commented
      print(inj.memory['i'])
      inj.memory['i'] = 0x12
      # inj.memory[0x20000000:0x20000004] = [0x1234, 0x5678] ## This works, it just doesn't point to valid memory so it's commented
      # inj.memory[0x20000000 + random.randint(0, 10)] |= 0b000010000 ## This works, it just doesn't point to valid memory so it's commented

      """
      Experiment
      """
      def foo(inj: Injector) -> None:
         print(inj.memory['i'])
         inj.memory['i'] = 0x1234
         print(inj.regs['rax'])

      print(inj.run(
         timeout=timedelta(seconds=1),
         injection_delay=timedelta(seconds=1),
         inject_func=foo,
      ))

      """
      Look at the memory and registers
      """
      # print(inj.memory[0x20000000])  ## This works, it just doesn't point to valid memory so it's commented

      runs.append({
         'i' : inj.memory['i'],
      })

   inj.close()
