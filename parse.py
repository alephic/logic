
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
SYM = re.compile(r'[^()\[\]\s\{\}<>*?]+')
SPACES = re.compile(r'\s*')
ASTERISK = re.compile(r'\*')
QUESTION = re.compile(r'\?')

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

def parse_sym(t, ref_ids):
  reset = t.pos
  s = parse_re(SYM, t)
  if not s:
    t.pos = reset
    return None
  if s in ref_ids:
    return Ref(s)
  return Sym(s)

def parse_arbitrary(t):
  if parse_re(QUESTION, t):
    return ARBITRARY

def parse_lambda(t, ref_ids):
  reset = t.pos
  if parse_re(LANGLE, t):
    parse_re(SPACES, t)
    m1 = parse_re(SYM, t)
    if m1:
      ref_ids = Scope(ref_ids)
      ref_ids[m1] = True
      parse_re(SPACES, t)
      if parse_re(RANGLE, t):
        parse_re(SPACES, t)
        m2 = parse_expr(t, ref_ids)
        if m2:
          return Lambda(m1, m2)
  t.pos = reset
  return None

def parse_expr(t, ref_ids):
  reset = t.pos
  curr = parse_expr_not_apply(t, ref_ids)
  if curr:
    while True:
      parse_re(SPACES, t)
      new = parse_expr_not_apply(t, ref_ids)
      if new:
        curr = Apply(curr, new)
      else:
        return curr
  t.pos = reset
  return None

def parse_expr_not_apply(t, ref_ids):
  return parse_paren_expr(t, ref_ids) \
    or parse_lambda(t, ref_ids) \
    or parse_sym(t, ref_ids) \
    or parse_arbitrary(t)

def parse_paren_expr(t, ref_ids):
  reset = t.pos
  if parse_re(LPAREN, t):
    parse_re(SPACES, t)
    m = parse_expr(t, ref_ids)
    if m:
      parse_re(SPACES, t)
      if parse_re(RPAREN, t):
        return m
  t.pos = reset
  return None

def parse(s, ref_ids):
  return parse_expr(Tracker(s), ref_ids)

def evaluate(s):
  return parse(s).evaluate({}, EMPTY)