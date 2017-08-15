
import re
from logic import *

LPAREN = re.compile(r'\(')
RPAREN = re.compile(r'\)')
LBRACK = re.compile(r'\[')
RBRACK = re.compile(r'\]')
SYM = re.compile(r'[^()\[\]\$@\s]+')
VAR = re.compile(r'\$')
PATTERN = re.compile(r'@')
SPACES = re.compile(r'\s*')

class Tracker:
  def __init__(self, s, pos=0):
    self.s = s
    self.pos = pos

def parse_re(r, t):
  m = r.match(t.s, pos=t.pos)
  if m:
    t.pos = m.end()
    return m.group(0)
  return None

def parse_rel(t):
  reset = t.pos
  if parse_re(LPAREN, t):
    components = []
    while True:
      parse_re(SPACES, t)
      if parse_re(RPAREN, t):
        if len(components) == 3 and isinstance(components[1], Sym) and components[1].sym_id == '->':
          return Lambda(components[0], components[2])
        else:
          return Rel(*components)
      else:
        m = parse_expr(t)
        if m:
          components.append(m)
        else:
          t.pos = reset
          return None
  else:
    t.pos = reset
    return None

def parse_apply(t):
  reset = t.pos
  if parse_re(LBRACK, t):
    parse_re(SPACES, t)
    m1 = parse_expr(t)
    if m1:
      parse_re(SPACES, t)
      m2 = parse_expr(t)
      if m2:
        parse_re(SPACES, t)
        if parse_re(RBRACK, t):
          return Apply(m1, m2)
  t.pos = reset
  return None

def parse_var(t):
  reset = t.pos
  if parse_re(VAR, t):
    m = parse_re(SYM, t)
    if m:
      if parse_re(PATTERN, t):
        m2 = parse_expr(t)
        if m2:
          return PatternVar(m, m2)
        else:
          t.pos = reset
          return None
      else:
        return Var(m)
  else:
    t.pos = reset
    return None

def parse_sym(t):
  m = parse_re(SYM, t)
  if m:
    return Gap() if m == '_' else Sym(m)
  else:
    return None

def parse_expr(t):
  return parse_rel(t) or parse_apply(t) or parse_var(t) or parse_sym(t)

def parse(s):
  return parse_expr(Tracker(s))

def evaluate(s):
  return parse(s).evaluate({}, None)

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
          print(p.evaluate(bindings, None))
        except LogicError as e:
          print(e.message)
      else:
        print('Invalid syntax')

if __name__ == "__main__":
  repl()