
from parse import *
import logic
import readline

def repl():
  bindings = {}
  world = World()
  while True:
    i = input('> ')
    if len(i) > 0:
      if i.startswith(':q'):
        return
      if i.startswith(':def'):
        t = Tracker(i, pos=4)
        parse_re(SPACES, t)
        sym = parse_re(SYM, t)
        parse_re(SPACES, t)
        expr = parse_expr(t, bindings).evaluate(bindings, world)
        if expr:
          bindings[sym] = expr
          print('%s := %s' % (sym, repr(expr)))
        continue
      if i.startswith(':decl'):
        t = Tracker(i, pos=5)
        parse_re(SPACES, t)
        expr = parse_expr(t, bindings).evaluate(bindings, world)
        if expr:
          world.add_fact(expr)
          print(repr(expr))
        continue
      p = parse(i, bindings)
      if p:
        try:
          print(p.evaluate(bindings, world))
        except LogicError as e:
          print(e.message)
      else:
        print('Invalid syntax')

if __name__ == "__main__":
  repl()