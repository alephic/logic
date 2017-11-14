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

class ArbitraryVal(Expression):
  counter = 0
  def __init__(self):
    self.num = ArbitraryVal.counter
    ArbitraryVal.counter += 1
  def subst(self, bindings):
    return self
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
    return ArbitraryVal()
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
    return self
  def match(self, other, bindings):
    return self.__eq__(other)
  def __eq__(self, other):
    return isinstance(other, Sym) and self.sym_id == other.sym_id
  def __hash__(self):
    return hash(self.sym_id)
  def collect_ref_ids(self, ref_ids):
    pass

class Ref(Expression):
  def __init__(self, ref_id):
    self.ref_id = ref_id
  def __repr__(self):
    return str(self.ref_id)
  def subst(self, bindings):
    if self.ref_id in bindings:
      return bindings[self.ref_id]
    else:
      return self
  def match(self, other, bindings):
    if self.ref_id in bindings:
      return bindings[self.ref_id] == other
    else:
      bindings[self.ref_id] = other
      return True
  def __eq__(self, other):
    return isinstance(other, Ref) and self.ref_id == other.ref_id
  def __hash__(self):
    return hash(Ref) ^ hash(self.ref_id)
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
    a = list(self.arg_expr.subst(bindings))
    for p_v in self.pred_expr.subst(bindings):
      for a_v in a:
        yield Apply(p_v, a_v)
  def match(self, other, bindings):
    return isinstance(other, Apply) \
      and self.pred_expr.match(other.pred_expr, bindings) \
      and self.arg_expr.match(other.arg_expr, bindings)
  def evaluate(self, bindings, world):
    p_v = self.pred_expr.evaluate(bindings, world)
    a_v = self.arg_expr.evaluate(bindings, world)
    if isinstance(p_v, Lambda):
      s = Scope(bindings)
      s[p_v.arg_id] = a_v
      return p_v.body.evaluate(s, world)
    else:
      return Apply(p_v, a_v)
  def __eq__(self, other):
    return isinstance(other, Apply) and self.pred_expr == other.pred_expr and self.arg_expr == other.arg_expr
  def __hash__(self):
    return hash(self.pred_expr) ^ hash(self.arg_expr)
  def collect_ref_ids(self, ref_ids):
    self.pred_expr.collect_ref_ids(ref_ids)
    self.arg_expr.collect_ref_ids(ref_ids)
