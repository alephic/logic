
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
    self.
  def check(self, claim):
    return False

EMPTY = World()

class LogicError(Exception):
  def __init__(self, message):
    self.message = message

class Expression:
  def subst(self, bindings, subst_vars=False):
    raise NotImplementedError()
  def collect_var_ids(self, var_ids):
    raise NotImplementedError()
  def match(self, other, bindings):
    raise NotImplementedError()
  def __eq__(self, other):
    raise NotImplementedError()
  def evaluate(self, bindings, world):
    return self.subst(bindings)
  def repr_closed(self):
    return repr(self)

# A variable
class Var(Expression):
  def __init__(self, var_id):
    self.var_id = var_id
  def __repr__(self):
    return '$'+str(self.var_id)
  def __eq__(self, other):
    return isinstance(other, Var) and other.var_id == self.var_id
  def subst(self, bindings, subst_vars=False):
    return self if not subst_vars else bindings.get(self.var_id, self)
  def collect_var_ids(self, var_ids):
    var_ids[self.var_id] = self
  def match(self, other, bindings):
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
    return '$'+str(self.var_id)+'@'+self.pattern.repr_closed()
  def subst(self, bindings, subst_vars=False):
    if subst_vars and self.var_id in bindings:
      return bindings[self.var_id]
    return PatternVar(self.var_id, self.pattern.subst(bindings, subst_vars))
  def collect_var_ids(self, var_ids):
    var_ids[self.var_id] = self
    self.pattern.collect_var_ids(var_ids)
  def match(self, other, bindings):
    if self.var_id in bindings:
      return bindings[self.var_id] == other
    elif self.pattern.match(other, bindings):
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
  def subst(self, bindings, subst_vars=False):
    return bindings[self.sym_id] if (self.sym_id in bindings) and subst_vars else self
  def collect_var_ids(self, var_ids):
    pass
  def match(self, other, bindings):
    return self.__eq__(other)
  def __eq__(self, other):
    return isinstance(other, Sym) and self.sym_id == other.sym_id

# Pattern-match wildcard
class Gap(Expression):
  def __repr__(self):
    return '_'
  def subst(self, bindings, subst_vars=False):
    return self
  def collect_var_ids(self, var_ids):
    pass
  def match(self, other, bindings):
    return True
  def __eq__(self, other):
    return isinstance(other, Gap)

class Rel(Expression):
  def __init__(self, *components):
    self.components = components
  def __repr__(self):
    return ' '.join((c.repr_closed() for c in self.components))
  def repr_closed(self):
    return '('+repr(self)+')'
  def subst(self, bindings, subst_vars=False):
    return Rel(*(c.subst(bindings, subst_vars) for c in self.components))
  def collect_var_ids(self, var_ids):
    for c in self.components:
      c.collect_var_ids(var_ids)
  def match(self, other, bindings):
    if not (isinstance(other, Rel) and len(self.components) == len(other.components)):
      return False
    for (c1, c2) in zip(self.components, other.components):
      if not c1.match(c2, bindings):
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
  def repr_closed(self):
    return '('+repr(self)+')'
  def subst(self, bindings, subst_vars=False):
    shadow = Shadow(bindings)
    self.arg_pattern.collect_var_ids(shadow.shadowed)
    if self.arg_constraint:
      self.arg_constraint.collect_var_ids(shadow.shadowed)
    return Lambda(self.arg_pattern.subst(shadow, subst_vars), self.arg_constraint.subst(shadow, subst_vars), self.body.subst(shadow, subst_vars))
  def collect_var_ids(self, var_ids):
    pass
  def match(self, other, bindings):
    return False
  def __eq__(self, other):
    return False
  
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
  def subst(self, bindings, subst_vars=False):
    return Apply(self.pred_expr.subst(bindings, subst_vars), self.arg_expr.subst(bindings, subst_vars))
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
      if isinstance(pred_val, Rel):
        return Rel(*pred_val.components, arg_val)
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

class Query(Expression):
  def __init__(self, val_pattern, val_constraint):
    self.val_pattern = val_pattern
    self.val_constraint = val_constraint
  def __repr__(self):
    return '['+repr(self.val_pattern)+': '+repr(self.val_constraint)+']'
  def subst(self, bindings, subst_vars=False):
    shadow = Shadow(bindings)
    self.val_pattern.collect_var_ids(shadow.shadowed)
    self.val_constraint.collect_var_ids(shadow.shadowed)
    return Query(self.val_pattern.subst(shadow, subst_vars), self.val_constraint.subst(shadow, subst_vars))
  def evaluate(self, bindings, world):
    evald = self.val_constraint.evaluate(bindings, world)
    check_res = world.check(evald)
    scope = Scope(bindings)
    evald.match(check_res, scope)
    return self.val_pattern.evaluate(scope, world)
  def match(self, other, bindings):
    return False
  def __eq__(self, other):
    return False

class With(Expression):
  def __init__(self, with_expr, body):
    self.with_expr = with_expr
    self.body = body
  def __repr__(self):
    return '{'+repr(self.with_expr)+'} '+repr(self.body)
  def repr_closed(self):
    return '('+repr(self)+')'
  def subst(self, bindings, subst_vars=False):
    return With(self.with_expr.subst(bindings, subst_vars), self.body.subst(bindings, subst_vars))
  def match(self, other, bindings):
    return isinstance(other, With) and self.with_expr.match(other.with_expr, bindings) and self.body.match(other.body, bindings)
  def __eq__(self, other):
    return isinstance(other, With) and self.with_expr == other.with_expr and self.body == other.body
  def evaluate(self, bindings, world):
    evald = self.with_expr.evaluate(bindings)
    # TODO: add evald to scoped world
    scoped_world = world
    return self.body.evaluate(bindings, scoped_world)