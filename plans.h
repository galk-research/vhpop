/* -*-C++-*- */
/*
 * Partial plans, and their components.
 *
 * $Id: plans.h,v 1.8 2001-08-11 06:17:43 lorens Exp $
 */
#ifndef PLANS_H
#define PLANS_H

#include <vector>
#include <stack>
#include <utility>
#include "support.h"
#include "domains.h"
#include "problems.h"
#include "bindings.h"
#include "costgraph.h"
#include "heuristics.h"


struct Reason;


/*
 * Abstract flaw.
 */
struct Flaw : public gc {
  /* Deletes this flaw. */
  virtual ~Flaw() {
  }

protected:
  /* Prints this flaw on the given stream. */
  virtual void print(ostream& os) const = 0;

  friend ostream& operator<<(ostream& os, const Flaw& f);
};

/* Output operator for flaws. */
inline ostream& operator<<(ostream& os, const Flaw& f) {
  f.print(os);
  return os;
}


/*
 * Open condition.
 */
struct OpenCondition : public Flaw {
  /* Open condition. */
  const Formula& condition;
  /* Id of step to which this open condition belongs. */
  const size_t step_id;
  /* Reason for open condition. */
  const Reason& reason;

  /* Constructs an open condition. */
  OpenCondition(const Formula& condition, size_t step_id, const Reason& reason)
    : condition(condition), step_id(step_id), reason(reason) {
  }

protected:
  /* Prints this open condition on the given stream. */
  void print(ostream& os) const;
};


/*
 * Chain of open conditions.
 */
typedef Chain<const OpenCondition*> OpenConditionChain;


struct Link;

/*
 * Threatened causal link.
 */
struct Unsafe : public Flaw {
  /* Threatened link. */
  const Link& link;
  /* Id of threatening step. */
  const size_t step_id;
  /* Threatening effect. */
  const Effect& effect;
  /* Specific part of effect that threatens link. */
  const Formula& effect_add;

  /* Constructs a threatened causal link. */
  Unsafe(const Link& link, size_t step_id, const Effect& effect,
	 const Formula& effect_add)
    : link(link), step_id(step_id), effect(effect), effect_add(effect_add) {
  }

protected:
  /* Prints this threatened causal link on the given stream. */
  virtual void print(ostream& os) const;
};


/*
 * Chain of threatened causal links.
 */
typedef Chain<const Unsafe*> UnsafeChain;


/*
 * Causal link.
 */
struct Link : public gc {
  /* Id of step that link goes from. */
  const size_t from_id;
  /* Id of step that link goes to. */
  const size_t to_id;
  /* Condition satisfied by link. */
  const Formula& condition;
  /* Reason for link. */
  const Reason& reason;

  /* Constructs a causal link. */
  Link(size_t from_id, const OpenCondition& open_cond)
    : from_id(from_id), to_id(open_cond.step_id),
      condition(open_cond.condition), reason(open_cond.reason) {
  }

private:
  /* Prints this causal link. */
  void print(ostream& os) const;

  friend ostream& operator<<(ostream& os, const Link& l);
};

/* Output operator for causal links. */
inline ostream& operator<<(ostream& os, const Link& l) {
  l.print(os);
  return os;
}


/*
 * Chain of causal links.
 */
typedef Chain<const Link*> LinkChain;


/*
 * Plan step.
 */
struct Step : public gc {
  /* Step id. */
  const size_t id;
  /* Action formula, or NULL if step is not instantiated from an action. */
  const AtomicFormula* const action;
  /* Precondition of step, or NULL if step has no precondition. */
  const Formula& precondition;
  /* List of effects. */
  const EffectList& effects;
  /* Reason for step. */
  const Reason& reason;

  /* Constructs a step. */
  Step(size_t id, const Formula& precondition, const EffectList& effects,
       const Reason& reason)
    : id(id), action(NULL), precondition(precondition.instantiation(id)),
      effects(effects.instantiation(id)), reason(reason) {
  }

  /* Constructs a step instantiated from an action. */
  Step(size_t id, const Action& action, const Reason& reason)
    : id(id), action(&action.action_formula(id)),
      precondition(action.precondition.instantiation(id)),
      effects(action.effects.instantiation(id)), reason(reason) {
  }

  /* Returns a copy of this step with a new reason. */
  const Step& new_reason(const Reason& reason) const {
    return *(new Step(id, action, precondition, effects, reason));
  }

private:
  /* Constructs a step. */
  Step(size_t id, const AtomicFormula* action, const Formula& precondition,
       const EffectList& effects, const Reason& reason)
    : id(id), action(action), precondition(precondition), effects(effects),
      reason(reason) {
  }
};


/*
 * Chain of plan steps.
 */
typedef Chain<const Step*> StepChain;


/*
 * Ordering constraint between plan steps.
 */
struct Ordering : public gc {
  /* Preceeding step. */
  const size_t before_id;
  /* Succeeding step. */
  const size_t after_id;
  /* Reason for ordering constraint. */
  const Reason& reason;

  /* Constructs an ordering constraint. */
  Ordering(size_t before_id, size_t after_id, const Reason& reason)
    : before_id(before_id), after_id(after_id), reason(reason) {
  }

private:
  /* Prints this ordering constraint on the given stream. */
  void print(ostream& os) const;

  friend ostream& operator<<(ostream& os, const Ordering& o);
};

/* Output operator for ordering constraints. */
inline ostream& operator<<(ostream& os, const Ordering& o) {
  o.print(os);
  return os;
}


/*
 * Chain of ordering constraints.
 */
typedef Chain<const Ordering*> OrderingChain;


/*
 * Collection of ordering constraints.
 */
struct Orderings : public gc {
  /* Constructs an empty ordering collection. */
  Orderings()
    : orderings_(NULL), size_(0) {
  }

  /* Constructs an ordering collection. */
  Orderings(const StepChain* steps, const OrderingChain* orderings);

  /* Checks if the first step is ordered before the second step. */
  bool before(size_t id1, size_t id2) const;

  /* Checks if the first step is ordered after the second step. */
  bool after(size_t id1, size_t id2) const;

  /* Checks if the first step could be ordered before the second step. */
  bool possibly_before(size_t id1, size_t id2) const;

  /* Checks if the first step could be ordered after the second step. */
  bool possibly_after(size_t id1, size_t id2) const;

  /* Returns the the ordering collection with the given additions. */
  const Orderings& refine(const Ordering& new_ordering,
			  const Step* new_step = NULL) const;

  /* Returns the ordering constraints making up this collection. */
  const OrderingChain* orderings() const {
    return orderings_;
  }

private:
  /* A step id map. */
  typedef hash_map<size_t, size_t> IdMap;

  /* The ordering constraints making up this collection. */
  const OrderingChain* orderings_;
  /* Number of steps. */
  size_t size_;
  /* Maps step ids to positions in the matrix below. */
  IdMap id_map1_;
  /* Maps positions in the matrix below to step ids */
  vector<size_t> id_map2_;
  /* Matrix representing the transitive closure of the ordering constraints. */
  vector<vector<bool> > order_;

  /* Updates the transitive closure given new ordering constraints. */
  void fill_transitive(const OrderingChain* orderings);

  /* Updates the transitive closure given a new ordering constraint. */
  void fill_transitive(const Ordering& ordering);

  /* Prints this ordering collection on the given stream. */
  void print(ostream& os) const;

  friend ostream& operator<<(ostream& os, const Orderings& o);
};

/* Output operator for ordering collections. */
inline ostream& operator<<(ostream& os, const Orderings& o) {
  o.print(os);
  return os;
}


/*
 * Hash function for open condition pointers.
 */
struct hash<const OpenCondition*> {
  size_t operator()(const OpenCondition* oc) const {
    return h(reinterpret_cast<int>(oc));
  }

private:
  hash<int> h;
};


/*
 * Plan.
 */
struct Plan : public gc {
  /* Id of goal step. */
  static const size_t GOAL_ID;

  /* Returns plan for given problem. */
  static const Plan* plan(const Problem& problem, Heuristic h, int e, bool g,
			  bool t, size_t limit, int v);

  /* Checks if this plan is complete. */
  bool complete() const;

  /* Returns the primary rank of this plan, where a lower rank
     signifies a better plan. */
  int primary_rank() const;

  /* Returns the secondary rank of this plan, where a lower rank
     signifies a better plan. */
  int secondary_rank() const;

  /* Returns the tertiary rank of this plan, where a lower rank
     signifies a better plan. */
  int tertiary_rank() const;

  /* Returns the number of open conditions of this plan. */
  size_t num_open_conds() const {
    return num_open_conds_;
  }

private:
  /* List of plans. */
  typedef vector<const Plan*, container_alloc> PlanList;
  /* Type of plan. */
  typedef enum { NORMAL_PLAN, INTERMEDIATE_PLAN, TRANSFORMED_PLAN } PlanType;

  /* Number of generated plans. */
  static size_t num_generated_plans;

  /* Chain of steps (could contain same step several times, if it is
     in plan for more than one reason). */
  const StepChain* const steps_;
  /* Number of unique steps in plan. */
  const size_t num_steps_;
  /* Highest step id that has been used so far. */
  const size_t high_step_id_;
  /* Chain of causal links. */
  const LinkChain* const links_;
  /* Number of causal links. */
  const size_t num_links_;
  /* Chain of potentially threatened links. */
  const UnsafeChain* const unsafes_;
  /* Number of potentially threatened links. */
  const size_t num_unsafes_;
  /* Chain of open conditions. */
  const OpenConditionChain* const open_conds_;
  /* Number of open conditions. */
  const size_t num_open_conds_;
  /* Number of static open condition. */
  const size_t num_static_open_conds_;
  /* Start of old open conditions. */
  const OpenConditionChain* const old_open_conds_;
  /* Binding constraints of this plan. */
  const Bindings& bindings_;
  /* Ordering constraints of this plan. */
  const Orderings& orderings_;
  /* Parent plan. */
  const Plan* const parent_;
  /* Plan type. */
  const PlanType type_;
  /* Rank of this plan. */
  int& rank1_;
  int& rank2_;
  const OpenCondition*& hardest_open_cond_;
  size_t& early_cost_;

  /* Returns the initial plan representing the given problem, or NULL
     if goals of problem are inconsistent. */
  static const Plan* make_initial_plan(const Problem& problem);

  /* Constructs a plan. */
  Plan(const StepChain* steps, size_t num_steps, size_t high_id,
       const LinkChain* links, size_t num_links,
       const UnsafeChain* unsafes, size_t num_unsafes,
       const OpenConditionChain* open_conds, size_t num_open_conds,
       size_t num_static_open_conds, const OpenConditionChain* old_open_conds,
       const Bindings& bindings, const Orderings& orderings,
       const Plan* parent, PlanType type = NORMAL_PLAN)
    : steps_(steps), num_steps_(num_steps), high_step_id_(high_id),
      links_(links), num_links_(num_links),
      unsafes_(unsafes), num_unsafes_(num_unsafes),
      open_conds_(open_conds), num_open_conds_(num_open_conds),
      num_static_open_conds_(num_static_open_conds),
      old_open_conds_(old_open_conds),
      bindings_(bindings), orderings_(orderings),
      parent_((parent != NULL && parent->type_ == INTERMEDIATE_PLAN) ?
	      parent->parent_ : parent),
      type_((parent != NULL && parent->type_ == INTERMEDIATE_PLAN) ?
	    TRANSFORMED_PLAN : type),
      rank1_(*(new (GC) int(-1))), rank2_(*(new (GC) int(-1))),
      hardest_open_cond_(*(new (GC) (const OpenCondition*)(NULL))),
      early_cost_(*new (GC) size_t(0)) {
    if (type_ != INTERMEDIATE_PLAN) {
      num_generated_plans++;
    }
  }

  const Flaw& get_flaw() const;

  void refinements(PlanList& new_plans) const;

  void handle_unsafe(PlanList& new_plans, const Unsafe& unsafe) const;

  void separate(PlanList& new_plans, const Unsafe& unsafe) const;

  void demote(PlanList& new_plans, const Unsafe& unsafe) const;

  void promote(PlanList& new_plans, const Unsafe& unsasfe) const;

  void new_ordering(PlanList& new_plans, const Ordering& ordering,
		    const Unsafe& unsafe) const;

  void relink(PlanList& new_plans, const Unsafe& unsafe) const;

  pair<const Plan*, const OpenCondition*> unlink(const Link& link) const;

  void handle_open_condition(PlanList& new_plans,
			     const OpenCondition& open_cond) const;

  void handle_disjunction(PlanList& new_plans,
			  const OpenCondition& open_cond) const;

  void add_step(PlanList& new_plans, const OpenCondition& open_cond) const;

  void link_preconditions(PlanList& new_plans) const;

  void reuse_step(PlanList& new_plans, const OpenCondition& open_cond,
		  bool early_linking = false) const;

  bool new_link(PlanList& new_plans, const Step& step,
		const OpenCondition& open_cond, const Link& link,
		const Reason& establish_reason,
		bool early_linking = false) const;

  void new_cw_link(PlanList& new_plans, const Step& step,
		   const OpenCondition& open_cond, const Link& link,
		   const Reason& establish_reason,
		   bool early_linking = false) const;

  const Plan* make_link(const Step& step, const Effect& effect,
			const OpenCondition& open_cond, const Link& link,
			const Reason& establish_reason,
			const SubstitutionList& unifier,
			bool early_linking = false) const;

  void print(ostream& os) const;

  bool duplicate() const;

  bool equivalent(const Plan& p) const;

  void h_rank() const;

  size_t make_node(CostGraph& cg,
		   hash_map<const OpenCondition*, size_t>& oc_nodes,
		   hash_map<size_t, size_t>& step_nodes,
		   hash_map<const Action*, size_t>& pred_nodes,
		   size_t step_id) const;

  size_t make_node(CostGraph& cg,
		   hash_map<size_t, size_t>& step_nodes,
		   hash_map<const Action*, size_t>& pred_nodes,
		   const Action& pred, size_t step_id) const;

  size_t make_node(CostGraph& cg,
		   hash_map<size_t, size_t>& step_nodes,
		   hash_map<const Action*, size_t>& pred_nodes,
		   const Formula& condition, size_t step_id) const;

  friend ostream& operator<<(ostream& os, const Plan& p);
};

/* Output operator for plans. */
inline ostream& operator<<(ostream& os, const Plan& p) {
  p.print(os);
  return os;
}

#endif /* PLANS_H */
