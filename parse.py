
import re
from logic import *

LPAREN = re.compile(r'\(')
RPAREN = re.compile(r'\)')
LBRACK = re.compile(r'\[')
RBRACK = re.compile(r'\]')
LBRACE = re.compile(r'\{')
RBRACE = re.compile(r'\}')
SYM = re.compile(r'[^()\[\]\$@\s\{\}]+')
GAP = re.compile(r'_')
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
  s = parse_re(SYM, t)
  if not s:
    t.pos = reset
    return None
  if s == '_':
    return Gap()
  parse_re(SPACES, t)
  if parse_re(LBRACE, t):
    components = []
    while True:
      parse_re(SPACES, t)
      if parse_re(RBRACE, t):
        if len(components) == 0:
          return Sym(s)
        return Rel(s, *components)
      else:
        m = parse_expr(t)
        if m:
          components.append(m)
        else:
          t.pos = reset
          return None
  else:
    return Sym(s)

def parse_apply(t):
  reset = t.pos
  if parse_re(LPAREN, t):
    parse_re(SPACES, t)
    m1 = parse_expr(t)
    if m1:
      parse_re(SPACES, t)
      m2 = parse_expr(t)
      if m2:
        parse_re(SPACES, t)
        if parse_re(RPAREN, t):
          return Apply(m1, m2)
  t.pos = reset
  return None

def parse_lambda(t):
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
          return Lambda(m1, m2)
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

def parse_expr(t):
  return parse_lambda(t) or parse_apply(t) or parse_var(t) or parse_rel(t)

def parse(s):
  return parse_expr(Tracker(s))

def evaluate(s):
  return parse(s).evaluate({}, None)