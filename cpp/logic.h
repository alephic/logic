#include <string>
#include <iostream>
#include <functional>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace std {

  template<> struct hash<logic::ValPtr> {
    std::size_t operator()(logic::ValPtr const& v) const {
      return v->hash();
    }
  };

  template<> struct equal_to<logic::ValPtr> {
    constexpr bool operator()(const logic::ValPtr& v1, const logic::ValPtr& v2) const {
      return *v1 == *v2;
    }
  };

}

namespace logic {

  typedef std::shared_ptr<const Value> ValPtr;
  typedef std::weak_ptr<const Value> ValPtrWeak;
  
  typedef std::string SymId;
  typedef std::unordered_set<ValPtr> ValSet;

  class Scope {
  protected:
    std::unordered_map<SymId, ValSet> data;
    Scope const *base;
  public:
    Scope() {}
    Scope(const Scope *base): base(base) {}
    void add(const SymId& k, ValSet& vs) {
      this->data[k] = vs;
    }
    const ValSet &get(const SymId& k) const {
      if (this->data.count(k)) {
        return this->data.at(k);
      } else {
        return this->base->get(k);
      }
    }
    bool has(const SymId& k) const {
      return this->data.count(k) || this->base->has(k);
    }
    virtual void squash_(std::unordered_map<SymId, ValSet>& out) const {
      if (this->base != nullptr) {
        this->base->squash_(out);
      }
      for (std::pair<SymId, ValSet>& kv : this->data) {
        out[kv.first] = kv.second;
      }
    }
    Scope squash() const {
      Scope s;
      this->squash_(s.data);
      return s;
    }
  };

  class Shadow: protected Scope {
  protected:
    std::unordered_set<SymId> shadowed;
  public:
    Shadow(const Scope *base): Scope(base) {}
    void shadow(const SymId& k) {
      this->shadow.insert(k);
    }
    bool has(const SymId& k) const {
      return this->data.count(k) || ((!this->shadowed.count(k)) && this->base->has(k));
    }
    void squash_(std::unordered_map<SymId, ValSet>& out) const {
      if (this->base != nullptr) {
        this->base->squash_(out);
      }
      for (const SymId& k : this->shadowed) {
        out.erase(k);
      }
      for (std::pair<SymId, ValSet>& kv : this->data) {
        out[kv.first] = kv.second;
      }
    }
  };

  class ValTree {
  private:
    std::unordered_map<ValPtr, ValTree> branches;
    std::unordered_map<ValPtr, ValPtr> leaves;
    void add_(std::vector<ValPtr>::iterator it, std::vector<ValPtr>::iterator end, ValPtr& p) {
      if (it+1 == end) {
        this->leaves[*it] = p;
      } else {
        if (!this->branches.count(*it)) {
          this->branches[*it] = ValTree();
        }
        this->branches[*it].add_(it+1, end, p);
      }
    }
  public:
    ValTree() {}
    void add(ValPtr& p) {
      std::vector<ValPtr> v;
      p->flatten(v);
      this->add_(v.begin(), v.end(), p);
    }
    void get_matches(std::vector<ValPtr>::iterator it, std::vector<ValPtr>::iterator end, Scope b, std::vector<std::pair<ValPtr, Scope>>& out) const {
      if (it+1 == end) {
        for (const std::pair<const ValPtr, ValPtr>& leaf : this->leaves) {
          Scope s = Scope(&b);
          if (leaf.first.match(*it, s)) {
            out.push_back(std::pair<ValPtr, Scope>{leaf.second, s.squash()});
          }
        }
      } else {
        for (const std::pair<const ValPtr, ValTree>& branch : this->branches) {
          Scope s = Scope(&b);
          if (branch.first.match(*it, s)) {
            branch.second.get_matches(it+1, end, s, out);
          }
        }
      }
    } 
  };

  class World {
  private:
    ValTree data;
    const World *base;
    void get_matches_(std::vector<ValPtr>& valFlat, std::vector<std::pair<ValPtr, Scope>>& out) const {
      if (this->base != nullptr) {
        this->base->get_matches_(valFlat, out);
      }
      this->data.get_matches(valFlat.begin(), valFlat.end(), Scope(), out);
    }
  public:
    World() {}
    World(const World *base) : base(base) {}
    void add(ValPtr& p) {
      this->data.add(p);
    }
    std::vector<std::pair<ValPtr, Scope>> get_matches(const ValPtr &p) const {
      std::vector<ValPtr> flat;
      p->flatten(flat);
      std::vector<std::pair<ValPtr, Scope>> v;
      this->get_matches_(flat, v);
      return v;
    }
  };

  class Value {
  public:
    ValPtrWeak self;
    virtual void repr(std::ostream&) const = 0;
    virtual void repr_closed(std::ostream& o) const {this->repr(o);}
    virtual ValSet subst(const Scope&) const = 0;
    virtual ValSet eval(const Scope& s, const World& w) const {return this->subst(s);}
    virtual bool match(const Value& other, Scope&) const {return *this == other;}
    virtual bool operator==(const Value&) const = 0;
    virtual std::size_t hash() const = 0;
    virtual void flatten(std::vector<ValPtr>& v) const {v.push_back(this->self.lock());}
    virtual void collectRefIds(std::unordered_set<SymId>& s) const {}
  };

  ValPtr bundle(Value *val) {
    ValPtr p(val);
    val->self = ValPtrWeak(p);
    return p;
  }

  class Sym: public Value {
  private:
    const SymId sym_id;
  public:
    Sym(const SymId &sym_id): sym_id(sym_id) {}
    void repr(std::ostream& o) const {
      o << this->sym_id;
    }
    ValSet subst(const Scope& s) const {
      return ValSet({this->self.lock()}, 1);
    }
    bool operator==(const Value& other) const {
      if (const Sym *s = dynamic_cast<const Sym *>(&other)) {
        if (this->sym_id == s->sym_id) {
          return true;
        }
      }
      return false;
    }
    std::size_t hash() const {
      return 85831957 ^ std::hash<std::string>{}(this->sym_id);
    }
  };
  
  class Wildcard: public Value {
  public:
    Wildcard() {}
    void repr(std::ostream& o) const {
      o << '*';
    }
    ValSet subst(const Scope& s) const {
      return ValSet({this->self.lock()}, 1);
    }
    bool operator==(const Value& other) const {
      if (const Wildcard *s = dynamic_cast<const Wildcard *>(&other)) {
        return true;
      }
    }
    std::size_t hash() const {
      return 12952153;
    }
  };

  Wildcard WILDCARD = bundle(new Wildcard());

  class WildcardTrace : public Value {
  private:
    const SymId ref_id;
  public:
    WildcardTrace(const SymId& ref_id) : ref_id(ref_id) {}
    void repr(std::ostream& o) const {
      o << '*';
    }
    ValSet subst(const Scope& s) const {
      if (s.has(this->ref_id)) {
        return s.get(this->ref_id);
      }
      return ValSet({this->self.lock()}, 1);
    }
    bool operator==(const Value& other) const {
      if (const WildcardTrace *s = dynamic_cast<const WildcardTrace *>(&other)) {
        if (this->ref_id == s->ref_id) {
          return true;
        }
      }
      return false;
    }
    std::size_t hash() const {
      return 53815931 ^ std::hash<std::string>{}(this->ref_id);
    }
    void collectRefIds(std::unordered_set<SymId>& s) const {
      s.insert(this->ref_id);
    }
  };

  class Ref : public Value {
  private:
    const SymId ref_id;
  public:
    Ref(const SymId& ref_id) : ref_id(ref_id) {}
    void repr(std::ostream& o) const {
      o << this->ref_id;
    }
    ValSet subst(const Scope& s) const {
      if (s.has(this->ref_id)) {
        const ValSet& vs = s.get(this->ref_id);
        if (vs.count(WILDCARD)) {
          ValSet vs2(vs);
          vs2.erase(WILDCARD);
          vs2.insert(bundle(new WildcardTrace(this->ref_id)));
          return vs2;
        }
        return vs;
      }
      return ValSet({this->self.lock()}, 1);
    }
    bool match(const ValPtr& other, Scope& s) const {
      if (s.has(this->ref_id)) {
        const ValSet& vs = s.get(this->ref_id);
        if (vs.count(other)) {
          return true;
        } else {
          return false;
        }
      } else {
        ValSet vs({other}, 1);
        s.add(this->ref_id, vs);
        return true;
      }
    }
    bool operator==(const Value& other) const {
      if (const Ref *s = dynamic_cast<const Ref *>(&other)) {
        if (this->ref_id == s->ref_id) {
          return true;
        }
      }
      return false;
    }
    std::size_t hash() const {
      return 128582195 ^ std::hash<std::string>{}(this->ref_id);
    }
    void collectRefIds(std::unordered_set<SymId>& s) const {
      s.insert(this->ref_id);
    }
  };

  class Arbitrary: public Value {
  public:
    Arbitrary() {}
    void repr(std::ostream& o) const {
      o << '?';
    }
    ValSet subst(const Scope& s) const {
      return ValSet({this->self.lock()}, 1);
    }
    ValSet eval(const Scope& s, const World& w) const {
      return ValSet({bundle(new ArbitraryInstance())}, 1);
    }
    bool operator==(const Value& other) const {
      if (const Arbitrary *s = dynamic_cast<const Arbitrary *>(&other)) {
        return true;
      }
      return false;
    }
    std::size_t hash() const {
      return 95318557;
    }
  };

  ValPtr ARBITRARY = bundle(new Arbitrary());

  class ArbitraryInstance: public Value {
  private:
    static std::size_t count;
    std::size_t id;
  public:
    ArbitraryInstance() {
      this->id = count;
      ++count;
    }
    void repr(std::ostream& o) const {
      o << '?' << id;
    }
    ValSet subst(const Scope& s) const {
      return ValSet({this->self.lock()}, 1);
    }
    bool operator==(const Value& other) const {
      if (const ArbitraryInstance *s = dynamic_cast<const ArbitraryInstance *>(&other)) {
        if (this->id == s->id) {
          return true;
        }
      }
      return false;
    }
    std::size_t hash() const {
      return 998439321 ^ this->id;
    }
  };

  class Lambda: public Value {
  private:
    static std::size_t count;
    std::size_t id;
  public:
    const SymId arg_id;
    const ValPtr body;
    Lambda(const SymId& arg_id, const ValPtr& body) : arg_id(arg_id), body(body) {
      this->id = count;
      ++count;
    }
    void repr(std::ostream& o) const {
      o << '<' << this->arg_id << '>' << ' ';
      this->body->repr(o);
    }
    void repr_closed(std::ostream& o) const {
      o << '(';
      this->repr(o);
      o << ')';
    }
    ValSet subst(const Scope& s) const {
      Shadow sh = Shadow(&s);
      sh.shadow(this->arg_id);
      ValSet bodySubstdVals = this->body->subst(sh);
      ValSet res(bodySubstdVals.bucket_count());
      for (ValPtr& bodySubstd : bodySubstdVals) {
        res.insert(bundle(new Lambda(this->arg_id, bodySubstd)));
      }
      return res;
    }
    bool operator==(const Value& other) const {
      if (const Lambda *s = dynamic_cast<const Lambda *>(&other)) {
        if (this->id == s->id) {
          return true;
        }
      }
      return false;
    }
    std::size_t hash() const {
      return 195218521 ^ this->id;
    }
  };

  class Apply: public Value {
  private:
    const ValPtr pred;
    const ValPtr arg;
  public:
    Apply(const ValPtr& pred, const ValPtr& arg) : pred(pred), arg(arg) {}
    void repr(std::ostream& o) const {
      if (const Apply *s = dynamic_cast<const Apply *>(&this->pred.get())) {
        this->pred->repr(o);
        o << ' ';
        this->arg->repr_closed(o);
      } else {
        this->pred->repr_closed(o);
        o << ' ';
        this->arg->repr_closed(o);
      }
    }
    void repr_closed(std::ostream& o) const {
      o << '(';
      this->repr(o);
      o << ')';
    }
    ValSet subst(const Scope& s) const {
      ValSet predVals = this->pred->subst(s);
      ValSet argVals = this->arg->subst(s);
      ValSet res(predVals.bucket_count()*argVals.bucket_count());
      for (ValPtr& predVal : predVals) {
        for (ValPtr& argVal : argVals) {
          res.insert(bundle(new Apply(predVal, argVal)));
        }
      }
      return res;
    }
    ValSet eval(const Scope& s, const World& w) {
      ValSet predVals = this->pred->eval(s, w);
      ValSet argVals = this->arg->eval(s, w);
      ValSet res(predVals.bucket_count()*argVals.bucket_count());
      for (ValPtr& predVal : predVals) {
        if (const Lambda *l = dynamic_cast<const Lambda *>(predVal.get())) {
          Scope s2 = Scope(&s);
          s2.add(l->arg_id, argVals);

        }
      }
    }
    bool operator==(const Value& other) const {
      if (const Apply *s = dynamic_cast<const Apply *>(&other)) {
        if (*this->pred == *s->pred && *this->arg == *s->arg) {
          return true;
        }
      }
      return false;
    }
    std::size_t hash() const {
      return 9858124 ^ this->pred->hash() ^ this->arg->hash();
    }
  };

  class Declare: public Value {
  private:
    const ValPtr with;
    const ValPtr body;
  public:
    Declare(const ValPtr, const ValPtr);
  };

  class Constrain: public Value {
  private:
    const ValPtr constraint;
    const ValPtr body;
  public:
    Constrain(const ValPtr, const ValPtr);
  };
}