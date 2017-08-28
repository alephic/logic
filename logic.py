
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

class LogicError(Exception):
  def __init__(self, message):
    self.message = message

class Expression:
  def subst(self, bindings):
    raise NotImplementedError()
  def collect_var_ids(self, var_ids):
    raise NotImplementedError()
  def match(self, other, bindings):
    raise NotImplementedError()
  def __eq__(self, other):
    return self.match(other, {})
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
    return '$'+str(self.var_id)+'@'+repr(self.pattern)
  def subst(self, bindings):
    return bindings[self.var_id] if self.var_id in bindings \
      else PatternVar(self.var_id, self.pattern.subst(bindings))
  def collect_var_ids(self, var_ids):
    var_ids[self.var_id] = True
    self.pattern.collect_var_ids(var_ids)
  def match(self, other, bindings):
    if self.var_id in bindings:
      return bindings[self.var_id] == other
    elif self.pattern.match(other, bindings):
      bindings[self.var_id] = other
      return True
    else:
      return False

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
  def match(self, other, bindings):
    return isinstance(other, Sym) and self.sym_id == other.sym_id

# Pattern-match wildcard
class Gap(Expression):
  def __repr__(self):
    return '_'
  def subst(self, bindings):
    return self
  def collect_var_ids(self, var_ids):
    pass
  def match(self, other, bindings):
    return True

class Rel(Expression):
  def __init__(self, sym_id, *components):
    self.sym_id = sym_id
    self.components = components
  def __repr__(self):
    return str(self.sym_id)+'{'+' '.join(repr(c) for c in self.components)+'}'
  def subst(self, bindings):
    return Rel(self.sym_id, *(c.subst(bindings) for c in self.components))
  def collect_var_ids(self, var_ids):
    for c in self.components:
      c.collect_var_ids(var_ids)
  def match(self, other, bindings):
    if not (isinstance(other, Rel) and self.sym_id == other.sym_id and len(self.components) == len(other.components)):
      return False
    for (c1, c2) in zip(self.components, other.components):
      if not c1.match(c2, bindings):
        return False
    return True
  def evaluate(self, bindings, world):
    return Rel(self.sym_id, *(c.evaluate(bindings, world) for c in self.components))

class Lambda(Expression):
  def __init__(self, arg_pattern, body):
    self.arg_pattern = arg_pattern
    self.body = body
  def __repr__(self):
    return '['+repr(self.arg_pattern)+' '+repr(self.body)+']'
  def subst(self, bindings):
    shadow = Shadow(bindings)
    self.arg_pattern.collect_var_ids(shadow.shadowed)
    return Lambda(self.arg_pattern.subst(shadow), self.body.subst(shadow))
  def collect_var_ids(self, var_ids):
    self.arg_pattern.collect_var_ids(var_ids)
    self.body.collect_var_ids(var_ids)
  def match(self, other, bindings):
    return False
  
class Apply(Expression):
  def __init__(self, lambda_expr, arg_expr):
    self.lambda_expr = lambda_expr
    self.arg_expr = arg_expr
  def __repr__(self):
    return '('+repr(self.lambda_expr)+' '+repr(self.arg_expr)+')'
  def subst(self, bindings):
    return Apply(self.lambda_expr.subst(bindings), self.arg_expr.subst(bindings))
  def collect_var_ids(self, var_ids):
    self.lambda_expr.collect_var_ids(var_ids)
    self.arg_expr.collect_var_ids(var_ids)
  def match(self, other, bindings):
    # return False
    return isinstance(other, Apply) \
      and self.lambda_expr.match(other.lambda_expr) \
      and self.arg_expr.match(other.arg_expr)
  def evaluate(self, bindings, world):
    lambda_val = self.lambda_expr.evaluate(bindings, world)
    arg_val = self.arg_expr.evaluate(bindings, world)
    if not isinstance(lambda_val, Lambda):
      return Apply(lambda_val, arg_val)
    scope = Scope(bindings)
    shadow = Shadow(scope)
    lambda_val.arg_pattern.collect_var_ids(shadow.shadowed)
    if lambda_val.arg_pattern.match(arg_val, shadow):
      return lambda_val.body.evaluate(scope, world)
    else:
      raise LogicError("Failed to evaluate: Argument pattern %s doesn't match supplied value %s\n  in: %s" % (repr(lambda_val.arg_pattern), repr(arg_val), repr(self)))

