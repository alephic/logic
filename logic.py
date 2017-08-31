import itertools

class Scope(dict):
  def __init__(self, base_dict):
    super().__init__()
    self.base_dict = base_dict
  def __contains__(self, item):
    return super().__contains__(item) or self.base_dict.__contains__(item)
  def __getitem__(self, item):
    return super().__getitem__(item) if super().__contains__(item) else self.base_dict[item]

class Shadow:
  def __init__(self, base_dict, shadowed=None):
    self.base_dict = base_dict
    self.shadowed = shadowed if shadowed else {}
  def __contains__(self, item):
    return (item in self.base_dict) and not (item in self.shadowed)
  def __getitem__(self, item):
    return self.base_dict[item]
  def __setitem__(self, item, value):
    self.base_dict[item] = value
  def __repr__(self):
    return repr(self.base_dict)+' - '+repr(self.shadowed)

def squash(s):
  if isinstance(s, Scope):
    d = squash(s.base_dict)
    d.update(s)
    return d
  if isinstance(s, Shadow):
    d = squash(s.base_dict)
    for k in s.shadowed:
      if k in d:
        del d[k]
    return d
  return dict(s)

def flatten(expr):
  if isinstance(expr, Apply):
    for x in flatten(expr.pred_expr):
      yield x
    yield expr.arg_expr
  else:
    yield expr

class Fact:
  def __init__(self, expr):
    self.expr = expr
    self.positions = tuple(flatten(expr))

class Table:
  def __init__(self):
    self.branches = {}
    self.leaves = []
  def add(self, fact, i=0):
    if i >= len(fact.positions) - 1:
      self.leaves.append(fact)
    else:
      if fact.positions[i] not in self.branches:
        self.branches[fact.positions[i]] = Table()
      self.branches[fact.positions[i]].add(fact, i=i+1)
  def get_matches(self, pattern_flat, bindings, i=0):
    if i >= len(pattern_flat) - 1:
      for leaf in self.leaves:
        s = Scope(bindings)
        if pattern_flat[i].match(leaf.positions[i], s):
          yield leaf.expr, s
    for x, b in self.branches.items():
      s = Scope(bindings)
      if pattern_flat[i].match(x, s):
        for m, s in b.get_matches(pattern_flat, s, i=i+1):
          yield m, s

class World:
  def __init__(self):
    self.fact_table = Table()
  def get_matches(self, pattern):
    return self.fact_table.get_matches(tuple(flatten(pattern)), {})
  def add_fact(self, expr):
    self.fact_table.add(Fact(expr))

class ScopedWorld(World):
  def __init__(self, base):
    super().__init__()
    self.base = base
  def _get_matches(self, pattern):
    return super().get_matches(pattern)
  def get_matches(self, pattern):
    curr = self
    while isinstance(curr, ScopedWorld):
      for m, s in curr._get_matches(pattern):
        yield m, s
      curr = curr.base
    for m, s in curr.get_matches(pattern):
      yield m, s

EMPTY = World()

class LogicError(Exception):
  def __init__(self, message):
    self.message = message

class Expression:
  def subst(self, bindings):
    raise NotImplementedError()
  def match(self, other, bindings):
    raise NotImplementedError()
  def __eq__(self, other):
    raise NotImplementedError()
  def evaluate(self, bindings, world):
    return self.subst(bindings)
  def repr_closed(self):
    return repr(self)
  def collect_ref_ids(self, ref_ids):
    raise NotImplementedError()

class Wildcard(Expression):
  def subst(self, bindings):
    yield self
  def match(self, other, bindings):
    return True # TODO: is this correct?
  def __eq__(self, other):
    return isinstance(other, Wildcard)
  def __hash__(self):
    return hash(Wildcard)
  def __repr__(self):
    return '*'
  def collect_ref_ids(self, ref_ids):
    pass

WILDCARD = Wildcard()

class ArbitraryVal(Expression):
  counter = 0
  def __init__(self):
    self.num = ArbitraryVal.counter
    ArbitraryVal.counter += 1
  def subst(self, bindings):
    yield self
  def match(self, other, bindings):
    return self.__eq__(other)
  def __eq__(self, other):
    return self is other
  def __hash__(self):
    return id(self)
  def __repr__(self):
    return '?'+str(self.num)
  def collect_ref_ids(self, ref_ids):
    pass

class Arbitrary(Expression):
  def subst(self, bindings):
    yield self
  def match(self, other, bindings):
    return self.__eq__(other)
  def evaluate(self, bindings, world):
    yield ArbitraryVal()
  def __eq__(self, other):
    return isinstance(other, Arbitrary)
  def __hash__(self):
    return hash(Arbitrary)
  def __repr__(self):
    return '?'
  def collect_ref_ids(self, ref_ids):
    pass

ARBITRARY = Arbitrary()

# A symbol
class Sym(Expression):
  def __init__(self, sym_id):
    self.sym_id = sym_id
  def __repr__(self):
    return str(self.sym_id)
  def subst(self, bindings):
    yield self
  def match(self, other, bindings):
    return self.__eq__(other)
  def __eq__(self, other):
    return isinstance(other, Sym) and self.sym_id == other.sym_id
  def __hash__(self):
    return hash(self.sym_id)
  def collect_ref_ids(self, ref_ids):
    pass

class Ref(Expression):
  def __init__(self, sym_id):
    self.sym_id = sym_id
  def __repr__(self):
    return str(self.sym_id)
  def subst(self, bindings):
    if self.sym_id in bindings:
      for b in bindings[self.sym_id]:
        yield b
    else:
      yield self
  def match(self, other, bindings):
    if self.sym_id in bindings:
      for binding in bindings[self.sym_id]:
        if binding == other:
          if len(bindings[self.sym_id]) > 1:
            bindings[self.sym_id] = {other}
          return True
        elif binding == WILDCARD:
          bindings[self.sym_id] = {other}
          return True
      return False
    bindings[self.sym_id] = {other}
    return True
  def __eq__(self, other):
    return isinstance(other, Ref) and self.sym_id == other.sym_id
  def __hash__(self):
    return hash(self.sym_id)
  def collect_ref_ids(self, ref_ids):
    ref_ids[self.ref_id] = True

class Lambda(Expression):
  def __init__(self, arg_id, body):
    self.arg_id = arg_id
    self.body = body
  def __repr__(self):
    return '<'+str(self.arg_id)+'> '+repr(self.body)
  def repr_closed(self):
    return '('+repr(self)+')'
  def subst(self, bindings):
    shadow = Shadow(bindings)
    shadow.shadowed[self.arg_id] = True
    for b in self.body.subst(shadow):
      yield Lambda(self.arg_id, b)
  def match(self, other, bindings):
    return False
  def __eq__(self, other):
    return self is other
  def __hash__(self):
    return id(self)
  def collect_ref_ids(self, ref_ids):
    inner = {}
    self.body.collect_ref_ids(inner)
    if self.arg_id in inner:
      del inner[self.arg_id]
    ref_ids.update(inner)
  
class Apply(Expression):
  def __init__(self, pred_expr, arg_expr):
    self.pred_expr = pred_expr
    self.arg_expr = arg_expr
  def __repr__(self):
    if isinstance(self.pred_expr, Apply):
      return repr(self.pred_expr)+' '+self.arg_expr.repr_closed()
    return self.pred_expr.repr_closed()+' '+self.arg_expr.repr_closed()
  def repr_closed(self):
    return '('+repr(self)+')'
  def subst(self, bindings):
    a = list(self.pred_expr.subst(bindings))
    for p_v in self.pred_expr.subst(bindings):
      for a_v in a:
        yield Apply(p_v, a_v)
  def match(self, other, bindings):
    return isinstance(other, Apply) \
      and self.pred_expr.match(other.pred_expr, bindings) \
      and self.arg_expr.match(other.arg_expr, bindings)
  def evaluate(self, bindings, world):
    a = set(self.arg_expr.evaluate(bindings, world))
    for p_v in self.pred_expr.evaluate(bindings, world):
      if not isinstance(p_v, Lambda):
        for a_v in a:
          yield Apply(p_v, a_v)
      else:
        scope = Scope(bindings)
        scope[p_v.arg_id] = a
        for b_v in p_v.body.evaluate(scope, world):
          yield b_v
  def __eq__(self, other):
    return isinstance(other, Apply) and self.pred_expr == other.pred_expr and self.arg_expr == other.arg_expr
  def __hash__(self):
    return hash(self.pred_expr) ^ hash(self.arg_expr)
  def collect_ref_ids(self, ref_ids):
    self.pred_expr.collect_ref_ids(ref_ids)
    self.arg_expr.collect_ref_ids(ref_ids)

class Constraint(Expression):
  def __init__(self, constraint_expr, body):
    self.constraint_expr = constraint_expr
    self.body = body
  def __repr__(self):
    return '['+repr(self.constraint_expr)+'] '+repr(self.body)
  def repr_closed(self):
    return '('+repr(self)+')'
  def subst(self, bindings):
    b = list(self.body.subst(bindings))
    for c_v in self.constraint_expr.subst(bindings):
      for b_v in b:
        yield Constraint(c_v, b_v)
  def match(self, other, bindings):
    return isinstance(other, Constraint) and self.constraint_expr.match(other.constraint_expr, bindings) and self.body.match(other.body, bindings)
  def __eq__(self, other):
    return isinstance(other, Constraint) and self.constraint_expr == other.constraint_expr and self.body == other.body
  def __hash__(self):
    return hash(Constraint) ^ hash(self.constraint_expr) ^ hash(self.body)
  def evaluate(self, bindings, world):
    ref_ids = {}
    self.constraint_expr.collect_ref_ids(ref_ids)
    scope = Scope(bindings)
    for r_id in ref_ids:
      scope[r_id] = set()
    for evald_v in self.constraint_expr.evaluate(bindings, world):
      for m, s in world.get_matches(evald_v):
        for r_id, vs in squash(s).items():
          if r_id in ref_ids:
            scope[r_id].update(vs)
    return self.body.evaluate(scope, world)
  def collect_ref_ids(self, ref_ids):
    self.constraint_expr.collect_ref_ids(ref_ids)
    self.body.collect_ref_ids(ref_ids)

class With(Expression):
  def __init__(self, with_expr, body):
    self.with_expr = with_expr
    self.body = body
  def __repr__(self):
    return '{'+repr(self.with_expr)+'} '+repr(self.body)
  def repr_closed(self):
    return '('+repr(self)+')'
  def subst(self, bindings):
    return With(self.with_expr.subst(bindings), self.body.subst(bindings))
  def match(self, other, bindings):
    return isinstance(other, With) and self.with_expr.match(other.with_expr, bindings) and self.body.match(other.body, bindings)
  def __eq__(self, other):
    return isinstance(other, With) and self.with_expr == other.with_expr and self.body == other.body
  def __hash__(self):
    return hash(With) ^ hash(self.with_expr) ^ hash(self.body)
  def evaluate(self, bindings, world):
    evald = self.with_expr.evaluate(bindings, world)
    scoped_world = ScopedWorld(world)
    scoped_world.add_fact(evald)
    return self.body.evaluate(bindings, scoped_world)
  def collect_ref_ids(self, ref_ids):
    self.with_expr.collect_ref_ids(ref_ids)
    self.body.collect_ref_ids(ref_ids)