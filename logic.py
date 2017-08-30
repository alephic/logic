
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
    pass
  def check(self, claim):
    return False

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

# A symbol
class Sym(Expression):
  def __init__(self, sym_id):
    self.sym_id = sym_id
  def __repr__(self):
    return str(self.sym_id)
  def subst(self, bindings):
    return bindings[self.sym_id] if self.sym_id in bindings else self
  def match(self, other, bindings):
    return self.__eq__(other)
  def __eq__(self, other):
    return isinstance(other, Sym) and self.sym_id == other.sym_id

def list_ids(primary, corollaries):
  if len(corollaries) == 0:
    return str(primary)
  return str(primary) + '; '+', '.join(map(str, corollaries))

class Lambda(Expression):
  def __init__(self, arg_id, body, arg_constraint=None, corollary_ids=[]):
    self.arg_id = arg_id
    self.body = body
    self.arg_constraint = arg_constraint
    self.corollary_ids = corollary_ids
  def __repr__(self):
    if self.arg_constraint:
      return '<'+list_ids(self.arg_id, self.corollary_ids)+': '+repr(self.arg_constraint)+'> '+repr(self.body)
    return '<'+str(self.arg_id)+'> '+repr(self.body)
  def repr_closed(self):
    return '('+repr(self)+')'
  def subst(self, bindings):
    shadow = Shadow(bindings)
    shadow.shadowed[self.arg_id] = True
    for corollary_id in self.corollary_ids:
      shadow.shadowed[corollary_id] = True
    return Lambda(self.arg_id, self.arg_constraint.subst(shadow) if self.arg_constraint else None, self.body.subst(shadow))
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
      return Apply(pred_val, arg_val)
    shadow = Shadow(bindings)
    scope = Scope(shadow)
    scope[pred_val.arg_id] = arg_val
    for corollary_id in pred_val.corollary_ids:
      shadow.shadowed[corollary_id] = True
    if pred_val.arg_constraint:
      evald = pred_val.arg_constraint.evaluate(scope)
      check_res = world.check(evald)
      if check_res:
        evald.match(check_res, scope)
        return pred_val.body.evaluate(scope, world)
      raise LogicError("Failed to evaluate: Argument constraint %s not satisfied by argument value %s\n  in: %s" % (repr(pred_val.arg_constraint), repr(arg_val), repr(self)))
    return pred_val.body.evaluate(scope, world)
  def __eq__(self, other):
    return isinstance(other, Apply) and self.pred_expr == other.pred_expr and self.arg_expr == other.arg_expr

class Query(Expression):
  def __init__(self, val_id, val_constraint, corollary_ids=[]):
    self.val_id = val_id
    self.val_constraint = val_constraint
    self.corollary_ids = corollary_ids
  def __repr__(self):
    return '['+list_ids(self.val_id, self.corollary_ids)+': '+repr(self.val_constraint)+']'
  def subst(self, bindings):
    shadow = Shadow(bindings)
    shadow.shadowed[self.val_id] = True
    for corollary_id in self.corollary_ids:
      shadow.shadowed[corollary_id] = True
    return Query(self.val_id, self.val_constraint.subst(shadow))
  def evaluate(self, bindings, world):
    shadow = Shadow(bindings)
    shadow.shadowed[self.val_id] = True
    for corollary_id in self.corollary_ids:
      shadow.shadowed[corollary_id] = True
    evald = self.val_constraint.evaluate(shadow, world)
    check_res = world.check(evald)
    if not check_res:
      raise LogicError("No candidates found for %s in current environment\n  in: %s" % (repr(self.val_pattern), repr(self)))
    scope = Scope(shadow)
    evald.match(check_res, scope)
    return scope[self.val_id]
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
  def subst(self, bindings):
    return With(self.with_expr.subst(bindings), self.body.subst(bindings))
  def match(self, other, bindings):
    return isinstance(other, With) and self.with_expr.match(other.with_expr, bindings) and self.body.match(other.body, bindings)
  def __eq__(self, other):
    return isinstance(other, With) and self.with_expr == other.with_expr and self.body == other.body
  def evaluate(self, bindings, world):
    evald = self.with_expr.evaluate(bindings)
    # TODO: add evald to scoped world
    scoped_world = world
    return self.body.evaluate(bindings, scoped_world)