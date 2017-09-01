#include <string>
#include <functional>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace std {

  template<> struct hash<logic::ValPtr> {
    std::size_t operator()(logic::ValPtr const& p) const {
      return p->hash();
    }
  };

}

namespace logic {

  typedef std::shared_ptr<const Value> ValPtr;
  
  typedef std::string SymId;
  typedef std::unordered_set<ValPtr> ValSet;

  class Bindings {
  public:
    virtual void add(const SymId &, ValSet &) {}
    virtual const ValSet &get(const SymId & s) const {throw std::out_of_range("no binding for symbol \"" + s + "\"");}
    virtual bool has(const SymId &) const {return false;}
  };

  class Scope: public Bindings {
  protected:
    std::unordered_map<SymId, ValSet> data;
    Bindings const *base;
  public:
    Scope() {}
    Scope(const Bindings *base): base(base) {}
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
  };

  class Shadow: protected Scope {
  private:
    std::unordered_set<SymId> shadowed;
  public:
    Shadow(const Bindings *base): Scope(base) {}
    void shadow(const SymId& k) {
      this->shadow.insert(k);
    }
    bool has(const SymId& k) const {
      return this->data.count(k) || ((!this->shadowed.count(k)) && this->base->has(k));
    }
  };

  class FactTree {
  private:
    std::unordered_map<Value, FactTree> branches;
    std::unordered_map<Value, ValPtr> leaves;
    void add_(std::vector<Value *>::iterator it, std::vector<Value *>::iterator end, ValPtr& p) {
      if (it+1 == end) {
        this->leaves[**it] = p;
      } else {
        if (!this->branches.count(**it)) {
          this->branches[**it] = FactTree();
        }
        this->branches[**it].add_(it+1, end, p);
      }
    }
    std::unordered_set<std::pair<ValPtr, Bindings>> get_matches_(std::vector<Value *>::iterator it, std::vector<Value *>::iterator end, Bindings) {

    } 
  public:
    FactTree();
    void add(ValPtr& p) {
      std::vector<Value *> v;
      p->flatten(v);
      this->add_(v.begin(), v.end(), p);
    }
    std::unordered_set<std::pair<ValPtr, Bindings>> get_matches(const ValPtr& p) const {
      std::vector<Value *> v;
      p->flatten(v);
      return this->get_matches_(v.begin(), v.end(), Scope());
    }
  };

  class World {
  private:
    FactTree data;
    const World *base;
  public:
    World(const World *base);
    std::unordered_set<std::pair<std::shared_ptr<Value>, Bindings>> get_matches(const Value &);
  };

  class Value {
  public:
    virtual std::string repr() const = 0;
    virtual std::string repr_closed() const = 0;
    virtual ValSet subst(const Bindings &) const = 0;
    virtual ValSet eval(const Bindings &, const World &) const = 0;
    virtual bool match(const Value &, Bindings &) const = 0;
    virtual bool operator==(const Value &) const = 0;
    virtual std::size_t hash() const = 0;
    virtual void flatten(std::vector<Value>& v) const {v.push_back(*this);}
  };

  class Sym: public Value {
  private:
    const SymId sym_id;
  public:
    Sym(const SymId &sym_id): sym_id(sym_id) {}
    std::string repr();
    std::string repr_closed();
    ValSet subst(const Bindings &);
    ValSet eval(const Bindings &, const World &);
    bool Match(const Value &, Bindings &);
    bool operator==(const Value &);
    std::size_t hash();
  };

  class Ref: public Value {
  private:
    const SymId ref_id;
  public:
    Ref(const SymId &);
  };

  class Wildcard: public Value {
  public:
    Wildcard();
  };
  
  class WildcardTrace: public Value {
  private:
    const SymId ref_id;
  public:
    WildcardTrace(const SymId &);
  };

  class Arbitrary: public Value {
  private:
    static std::size_t count;
    std::size_t id;
  public:
    Arbitrary();
  };

  class Lambda: public Value {
  private:
    static std::size_t count;
    std::size_t id;
    const SymId arg_id;
    const ValPtr body;
  public:
    Lambda(const SymId, const ValPtr);
  };

  class Apply: public Value {
  private:
    const ValPtr pred;
    const ValPtr arg;
  public:
    Apply(const ValPtr, const ValPtr);
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