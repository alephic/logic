
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

class World:
  def __init__(self, facts=[]):
    self.facts = facts
  def check(self, claim):
    return False

EMPTY = World()

class LogicError(Exception):
  def __init__(self, message):
    self.message = message

class Expression:
  def subst(self, bindings):
    raise NotImplementedError()
  def collect_var_ids(self, var_ids):
    raise NotImplementedError()
  def match(self, other, bindings, world):
    raise NotImplementedError()
  def __eq__(self, other):
    raise NotImplementedError()
  def evaluate(self, bindings, world):
    return self.subst(bindings)

# A variable
class Var(Expression):
  def __init__(self, var_id):
    self.var_id = var_id
  def __repr__(self):
    return '$'+str(self.var_id)
  def __eq__(self, other):
    return isinstance(other, Var) and other.var_id == self.var_id
  def subst(self, bindings):
    return bindings[self.var_id] if self.var_id in bindings else self
  def collect_var_ids(self, var_ids):
    var_ids[self.var_id] = True
  def match(self, other, bindings, world):
    if self.var_id in bindings:
      return bindings[self.var_id] == other
    else:
      bindings[self.var_id] = other
      return True

# A variable with a specified pattern to match
class PatternVar(Expression):
  def __init__(self, var_id, pattern):
    self.var_id = var_id
    self.pattern = pattern
  def __repr__(self):
    return '$'+str(self.var_id)+'@'+repr(self.pattern)
  def subst(self, bindings):
    return bindings[self.var_id] if self.var_id in bindings \
      else PatternVar(self.var_id, self.pattern.subst(bindings))
  def collect_var_ids(self, var_ids):
    var_ids[self.var_id] = True
    self.pattern.collect_var_ids(var_ids)
  def match(self, other, bindings, world):
    if self.var_id in bindings:
      return bindings[self.var_id] == other
    elif self.pattern.match(other, bindings, world):
      bindings[self.var_id] = other
      return True
    else:
      return False
  def __eq__(self, other):
    return isinstance(other, PatternVar) and self.var_id == other.var_id and self.pattern == other.pattern

# A symbol
class Sym(Expression):
  def __init__(self, sym_id):
    self.sym_id = sym_id
  def __repr__(self):
    return str(self.sym_id)
  def subst(self, bindings):
    return self
  def collect_var_ids(self, var_ids):
    pass
  def match(self, other, bindings, world):
    return self.__eq__(other)
  def __eq__(self, other):
    return isinstance(other, Sym) and self.sym_id == other.sym_id

# Pattern-match wildcard
class Gap(Expression):
  def __repr__(self):
    return '_'
  def subst(self, bindings):
    return self
  def collect_var_ids(self, var_ids):
    pass
  def match(self, other, bindings, world):
    return True
  def __eq__(self, other):
    return isinstance(other, Gap)

class Rel(Expression):
  def __init__(self, *components):
    self.components = components
  def __repr__(self):
    return '('+' '.join(map(repr, self.components))+')'
  def subst(self, bindings):
    return Rel(*(c.subst(bindings) for c in self.components))
  def collect_var_ids(self, var_ids):
    for c in self.components:
      c.collect_var_ids(var_ids)
  def match(self, other, bindings, world):
    if not (isinstance(other, Rel) and len(self.components) == len(other.components)):
      return False
    for (c1, c2) in zip(self.components, other.components):
      if not c1.match(c2, bindings, world):
        return False
    return True
  def evaluate(self, bindings, world):
    return Rel(*(c.evaluate(bindings, world) for c in self.components))
  def __eq__(self, other):
    return isinstance(other, Rel) and self.components == other.components

class Lambda(Expression):
  def __init__(self, arg_pattern, arg_constraint, body):
    self.arg_pattern = arg_pattern
    self.arg_constraint = arg_constraint
    self.body = body
  def __repr__(self):
    if self.arg_constraint:
      return '<'+repr(self.arg_pattern)+': '+repr(self.arg_constraint)+'> '+repr(self.body)
    return '<'+repr(self.arg_pattern)+'> '+repr(self.body)
  def subst(self, bindings):
    shadow = Shadow(bindings)
    self.arg_pattern.collect_var_ids(shadow.shadowed)
    self.arg_constraint.collect_var_ids(shadow.shadowed)
    return Lambda(self.arg_pattern.subst(shadow), self.body.subst(shadow))
  def collect_var_ids(self, var_ids):
    self.arg_pattern.collect_var_ids(var_ids)
    self.arg_constraint.collect_var_ids(var_ids)
    self.body.collect_var_ids(var_ids)
  def match(self, other, bindings, world):
    return False
  def __eq__(self, other):
    if not isinstance(other, Lambda):
      return False
    b = {}
    if not self.arg_pattern.match(other.arg_pattern, b, EMPTY):
      return False
    if not self.arg_constraint.match(other.arg_constraint, b, EMPTY):
      return False
    return self.body.subst(b) == other.body
  
class Apply(Expression):
  def __init__(self, pred_expr, arg_expr):
    self.pred_expr = pred_expr
    self.arg_expr = arg_expr
  def __repr__(self):
    return '('+repr(self.pred_expr)+' '+repr(self.arg_expr)+')'
  def subst(self, bindings):
    return Apply(self.pred_expr.subst(bindings), self.arg_expr.subst(bindings))
  def collect_var_ids(self, var_ids):
    self.pred_expr.collect_var_ids(var_ids)
    self.arg_expr.collect_var_ids(var_ids)
  def match(self, other, bindings):
    # return False
    return isinstance(other, Apply) \
      and self.pred_expr.match(other.pred_expr, bindings) \
      and self.arg_expr.match(other.arg_expr, bindings)
  def evaluate(self, bindings, world):
    pred_val = self.pred_expr.evaluate(bindings, world)
    arg_val = self.arg_expr.evaluate(bindings, world)
    if not isinstance(pred_val, Lambda):
      return Rel(pred_val, arg_val)
    shadow = Shadow(bindings)
    scope = Scope(shadow)
    pred_val.arg_pattern.collect_var_ids(shadow.shadowed)
    if pred_val.arg_constraint:
      pred_val.arg_constraint.collect_var_ids(shadow.shadowed)
    if pred_val.arg_pattern.match(arg_val, scope):
      if pred_val.arg_constraint:
        evald = pred_val.arg_constraint.evaluate(scope)
        check_res = world.check(evald)
        if check_res:
          evald.match(check_res, scope)
          return pred_val.body.evaluate(scope, world)
        raise LogicError("Failed to evaluate: Argument constraint %s not satisfied by supplied value %s\n  in: %s" % (repr(pred_val.arg_constraint), repr(arg_val), repr(self)))
      return pred_val.body.evaluate(scope, world)
    else:
      raise LogicError("Failed to evaluate: Argument pattern %s doesn't match supplied value %s\n  in: %s" % (repr(pred_val.arg_pattern), repr(arg_val), repr(self)))
  def __eq__(self, other):
    return isinstance(other, Apply) and self.pred_expr == other.pred_expr and self.arg_expr == other.arg_expr
