
import re
from logic import *

LPAREN = re.compile(r'\(')
RPAREN = re.compile(r'\)')
LBRACK = re.compile(r'\[')
RBRACK = re.compile(r'\]')
LBRACE = re.compile(r'\{')
RBRACE = re.compile(r'\}')
LANGLE = re.compile(r'<')
RANGLE = re.compile(r'>')
SYM = re.compile(r'[^()\[\]\$@\s\{\}<>:]+')
VAR = re.compile(r'\$')
PATTERN = re.compile(r'@')
SPACES = re.compile(r'\s*')
COLON = re.compile(r':')

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

def parse_sym(t):
  reset = t.pos
  s = parse_re(SYM, t)
  if not s:
    t.pos = reset
    return None
  if s == '_':
    return Gap()
  return Sym(s)

def parse_apply(t):
  reset = t.pos
  parse_re(SPACES, t)
  m1 = parse_expr_not_apply(t)
  if m1:
    parse_re(SPACES, t)
    m2 = parse_expr(t)
    if m2:
      if isinstance(m2, Apply):
        return Apply(Apply(m1, m2.pred_expr), m2.arg_expr)
      return Apply(m1, m2)
  t.pos = reset
  return None

def parse_lambda(t):
  reset = t.pos
  if parse_re(LANGLE, t):
    parse_re(SPACES, t)
    m1 = parse_expr(t)
    if m1:
      parse_re(SPACES, t)
      c = parse_re(COLON, t)
      parse_re(SPACES, t)
      constraint = None
      if c:
        constraint = parse_expr(t)
        if not constraint:
          t.pos = reset
          return None
      if parse_re(RANGLE, t):
        parse_re(SPACES, t)
        m2 = parse_expr(t)
        if m2:
          return Lambda(m1, constraint, m2)
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

def parse_query(t):
  reset = t.pos
  if parse_re(LBRACK, t):
    parse_re(SPACES, t)
    m = parse_expr(t)
    if m:
      parse_re(SPACES, t)
      if parse_re(COLON, t):
        parse_re(SPACES, t)
        m2 = parse_expr(t)
        if m2:
          parse_re(SPACES, t)
          if parse_re(RBRACK, t):
            return Query(m, m2)
  t.pos = reset
  return None

def parse_with(t):
  reset = t.pos
  if parse_re(LBRACE, t):
    parse_re(SPACES, t)
    m = parse_expr(t)
    if m:
      parse_re(SPACES, t)
      if parse_re(RBRACE, t):
        parse_re(SPACES, t)
        m2 = parse_expr(t)
        if m2:
          return With(m, m2)
  t.pos = reset
  return None

def parse_expr(t):
  return parse_apply(t) or parse_expr_not_apply(t)

def parse_expr_not_apply(t):
  return parse_paren_expr(t) or parse_lambda(t) or parse_query(t) or parse_with(t) or parse_var(t) or parse_sym(t)

def parse_paren_expr(t):
  reset = t.pos
  if parse_re(LPAREN, t):
    parse_re(SPACES, t)
    m = parse_expr(t)
    if m:
      parse_re(SPACES, t)
      if parse_re(RPAREN, t):
        return m
  t.pos = reset
  return None

def parse(s):
  return parse_expr(Tracker(s))

def evaluate(s):
  return parse(s).evaluate({}, None)