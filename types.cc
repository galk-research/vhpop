/*
 * Copyright (C) 2002 Carnegie Mellon University
 * Written by H�kan L. S. Younes.
 *
 * Permission is hereby granted to distribute this software for
 * non-commercial research purposes, provided that this copyright
 * notice is included with any such distribution.
 *
 * THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
 * EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE.  THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE
 * SOFTWARE IS WITH YOU.  SHOULD THE PROGRAM PROVE DEFECTIVE, YOU
 * ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION.
 *
 * $Id: types.cc,v 3.2 2002-03-18 09:37:28 lorens Exp $
 */
#include "types.h"


/*
 * A subtype binary predicate.
 */
struct Subtype : public binary_function<const Type*, const Type*, bool> {
  /* Checks if the first type is a subtype of the second type. */
  bool operator()(const Type* t1, const Type* t2) const {
    return t1->subtype(*t2);
  }
};


/* ====================================================================== */
/* Type */

/* Checks if this type is the object type. */
bool Type::object() const {
  return this == &SimpleType::OBJECT;
}


/* ====================================================================== */
/* SimpleType */

/* The object type. */
const SimpleType SimpleType::OBJECT = SimpleType("object");


/* Constructs a simple type with the given name. */
SimpleType::SimpleType(const string& name, const Type& supertype)
  : name(name),
    supertype(name == "object" ? (const Type&) *this : supertype) {}


/* Checks if this type is a subtype of the given type. */
bool SimpleType::subtype(const Type& t) const {
  if (t.object()) {
    return true;
  } else {
    const SimpleType* st = dynamic_cast<const SimpleType*>(&t);
    if (st != NULL) {
      return name == st->name || (!object() && supertype.subtype(t));
    } else {
      const UnionType& ut = dynamic_cast<const UnionType&>(t);
      return member_if(ut.types().begin(), ut.types().end(),
		       bind1st(Subtype(), this));
    }
  }
}


/* Checks if this object is less than the given object. */
bool SimpleType::less(const LessThanComparable& o) const {
  const SimpleType& st = dynamic_cast<const SimpleType&>(o);
  return name < st.name;
}


/* Checks if this object equals the given object. */
bool SimpleType::equals(const EqualityComparable& o) const {
  const SimpleType* st = dynamic_cast<const SimpleType*>(&o);
  return st != NULL && name == st->name;
}


/* Prints this object on the given stream. */
void SimpleType::print(ostream& os) const {
  os << name;
}


/* ====================================================================== */
/* UnionType */

/* Returns the canonical form of the given union type. */
const Type& UnionType::simplify(const UnionType& t) {
  const Type* canonical_type;
  if (t.types_.empty()) {
    canonical_type = &SimpleType::OBJECT;
    delete &t;
  } else if (t.types_.size() == 1) {
    canonical_type = *t.types_.begin();
    delete &t;
  } else {
    canonical_type = &t;
  }
  return *canonical_type;
}


/* Returns the union of two types. */
const Type& UnionType::add(const Type& t1, const Type& t2) {
  UnionType* t;
  const SimpleType* st1 = dynamic_cast<const SimpleType*>(&t1);
  if (st1 != NULL) {
    t = new UnionType(*st1);
  } else {
    const UnionType& ut1 = dynamic_cast<const UnionType&>(t1);
    t = new UnionType(ut1);
  }
  const SimpleType* st2 = dynamic_cast<const SimpleType*>(&t2);
  if (st2 != NULL) {
    t->add(*st2);
  } else {
    const UnionType& ut2 = dynamic_cast<const UnionType&>(t2);
    for (TypeSetIter ti = ut2.types_.begin(); ti != ut2.types_.end(); ti++) {
      t->add(**ti);
    }
  }
  return simplify(*t);
}


/* Constructs a singleton union type. */
UnionType::UnionType(const SimpleType& type) {
  types_.insert(&type);
}


/* Constituent types. */
const TypeSet& UnionType::types() const {
  return types_;
}


/* Adds the given simple type to this union. */
void UnionType::add(const SimpleType& t) {
  if (!subtype(t)) {
    TypeSetIter ti =
      find_if(types_.begin(), types_.end(), bind1st(Subtype(), &t));
    while (ti != types_.end()) {
      types_.erase(ti);
      ti = find_if(types_.begin(), types_.end(), bind1st(Subtype(), &t));
    }
    types_.insert(&t);
  }
}


/* Checks if this type is a subtype of the given type. */
bool UnionType::subtype(const Type& t) const {
  return member_if(types_.begin(), types_.end(), bind2nd(Subtype(), &t));
}


/* Checks if this object equals the given object. */
bool UnionType::equals(const EqualityComparable& o) const {
  const UnionType* ut = dynamic_cast<const UnionType*>(&o);
  return (ut != NULL && types_.size() == ut->types_.size()
	  && equal(types_.begin(), types_.end(), ut->types_.begin(),
		   equal_to<const EqualityComparable*>()));
}


/* Prints this object on the given stream. */
void UnionType::print(ostream& os) const {
  os << "(either";
  for (TypeSetIter ti = types_.begin(); ti != types_.end(); ti++) {
    os << ' ' << **ti;
  }
  os << ")";
}
