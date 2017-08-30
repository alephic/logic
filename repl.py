
from parse import *
import logic
import readline

def repl():
  bindings = {}
  while True:
    i = input('> ')
    if len(i) > 0:
      if i.startswith(':q'):
        return
      if i.startswith('#'):
        t = Tracker(i, pos=1)
        sym = parse_re(SYM, t)
        parse_re(SPACES, t)
        expr = parse_expr(t)
        if expr:
          bindings[sym] = expr
          print('Definition added for '+sym)
        continue
      p = parse(i)
      if p:
        try:
          print(p.evaluate(bindings, logic.EMPTY))
        except LogicError as e:
          print(e.message)
      else:
        print('Invalid syntax')

if __name__ == "__main__":
  repl()