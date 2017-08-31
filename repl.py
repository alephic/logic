
from parse import *
import logic
import readline

def str_alts(s):
  if len(s) == 1:
    return repr(next(iter(s)))
  else:
    return ' | '.join((x.repr_closed() for x in s))

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
        evald = set(parse_expr(t, bindings).evaluate(bindings, world))
        bindings[sym] = evald
        print('%s := %s' % (sym, str_alts(evald)))
        continue
      if i.startswith(':decl'):
        t = Tracker(i, pos=5)
        parse_re(SPACES, t)
        evald = set(parse_expr(t, bindings).evaluate(bindings, world))
        for evald_v in evald:
          world.add_fact(evald_v)
        print(str_alts(evald))
        continue
      p = parse(i, bindings)
      if p:
        try:
          print(str_alts(set(p.evaluate(bindings, world))))
        except LogicError as e:
          print(e.message)
      else:
        print('Invalid syntax')

if __name__ == "__main__":
  repl()