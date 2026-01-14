# Ontological Independence Test for basset-hound

**Date:** 2026-01-14
**Status:** Formal Test Framework Complete
**Purpose:** Provide a reusable test to evaluate whether something should be an entity in basset-hound

---

## Three Distinct Concepts

basset-hound distinguishes between three fundamentally different data concepts:

| Concept | Definition | Example | Status in basset-hound |
|---------|------------|---------|------------------------|
| **Ontologically Independent Entity** | Something that can exist and be clearly defined without requiring any relationship to another entity | Person, Platform, Location | First-class Node |
| **Ontologically Dependent Data** | Something that *by its very nature* cannot exist without another entity | Account (needs Platform), Content (needs Platform + Author) | Relationship properties or edge data |
| **Orphan Data** | Data that *temporarily* lacks a relationship but is not inherently dependent | Scraped profile data before entity linkage | Temporary storage (OrphanData node) |

---

## Key Distinction: Dependence vs Orphan

### Ontological Dependence (Inherent)

From [Stanford Encyclopedia of Philosophy - Ontological Dependence](https://plato.stanford.edu/entries/dependence/):

> "Ontological dependence is a relation—or, more accurately, a family of relations—between entities or beings... An entity is ontologically independent if it does not depend on anything else, meaning that it is fundamental and can exist on its own."

**Key insight:** Ontological dependence is an *inherent property* of the thing itself. An Account is *always* dependent on a Platform—this is part of what an Account *is*.

**Test:** Ask "Can this thing *ever* exist without X?" If the answer is always "no" regardless of circumstances, it is ontologically dependent.

### Orphan Data (Circumstantial)

From database management literature:

> "Orphan data is child data whose parent has been dropped or deleted" — Komprise

> "An orphan record is a record whose foreign key value references a non-existent primary key value" — Database.guide

**Key insight:** Orphan data is a *temporary state*, not an inherent property. The data *should* be linked to an entity but isn't *yet*. The entity it links to can exist—we just haven't made the connection.

**Test:** Ask "Could this data be linked to an existing entity type?" If yes, it's orphan data waiting for linkage.

---

## The Ontological Independence Test

### Primary Question

> **"Can this thing exist and be clearly defined WITHOUT requiring ANY relationship to another entity?"**

If YES → It is an **Entity** (Node)
If NO → It is **Dependent Data** (Relationship or Property)

### Secondary Tests

| Test | Question | If YES | If NO |
|------|----------|--------|-------|
| **Standalone Test** | Can it exist with zero relationships? | Entity | Likely dependent |
| **Definition Test** | Can you define it without mentioning another entity type? | Entity | Dependent |
| **Pipeline Test** | Is it where the "pipeline of influence" stops? | Entity | Pass-through |
| **Reference Test** | Do multiple other things need to reference it? | Entity | Could be property |
| **Query Test** | Would users search for it directly? | Entity | Could be property |

### Decision Matrix

```
START: "What is this thing?"
   │
   ├─► Can it exist without any relationship to another entity?
   │      │
   │      ├─► YES: Does it have independent identity?
   │      │      │
   │      │      ├─► YES ──► ENTITY (Node)
   │      │      │
   │      │      └─► NO ──► Consider as Property
   │      │
   │      └─► NO: Is this dependence inherent to its definition?
   │             │
   │             ├─► YES ──► DEPENDENT DATA (Relationship/Property)
   │             │
   │             └─► NO: Is it just missing a link?
   │                    │
   │                    ├─► YES ──► ORPHAN DATA (Temporary)
   │                    │
   │                    └─► NO ──► Re-evaluate definition
```

---

## Applied Examples

### Example 1: Person

| Test | Answer | Result |
|------|--------|--------|
| Can a Person exist without relationships? | YES - A person exists regardless of accounts, jobs, or affiliations | ✓ |
| Can you define "Person" without another entity? | YES - "A human individual with identity" | ✓ |
| Is Person where influence stops? | YES - Actions trace back to persons | ✓ |
| Do other things reference Person? | YES - Accounts, memberships, ownership | ✓ |

**Verdict: ENTITY** ✓

### Example 2: Platform

| Test | Answer | Result |
|------|--------|--------|
| Can a Platform exist without relationships? | YES - "A platform can simply just be a platform, a place where people interact and content is shared" | ✓ |
| Can you define "Platform" without another entity? | YES - "A digital space for interaction" | ✓ |
| Is Platform where influence stops? | YES - It's the context for accounts/content | ✓ |
| Do other things reference Platform? | YES - Multiple persons have accounts on same platform | ✓ |

**Verdict: ENTITY** ✓

### Example 3: Account

| Test | Answer | Result |
|------|--------|--------|
| Can an Account exist without relationships? | NO - "An account cannot exist without a platform to host it" | ✗ |
| Can you define "Account" without another entity? | NO - An account IS "a presence ON a platform" | ✗ |
| Is Account where influence stops? | NO - Pass-through between Person and Platform | ✗ |
| Do other things reference Account? | Rarely - usually you reference Person or Platform | ─ |

**Verdict: DEPENDENT DATA** (Relationship: HAS_ACCOUNT_ON)

### Example 4: Content (Post/Message)

| Test | Answer | Result |
|------|--------|--------|
| Can Content exist without relationships? | NO - Content requires Platform (where) and Author (who) | ✗ |
| Can you define "Content" without another entity? | NO - A post is "content ON a platform BY an author" | ✗ |
| Is Content where influence stops? | NO - Pass-through; influence flows to author | ✗ |
| Do other things reference Content? | Sometimes - but always via Platform/Author | ─ |

**Verdict: DEPENDENT DATA** (Properties on relationships)

### Example 5: Group

| Test | Answer | Result |
|------|--------|--------|
| Can a Group exist without relationships? | YES - "There can be 0 people in a group if all the people left" | ✓ |
| Can you define "Group" without another entity? | YES - "A collective entity with identity and purpose" | ✓ |
| Is Group where influence stops? | YES - Groups can be investigated directly | ✓ |
| Do other things reference Group? | YES - Members, locations, affiliations | ✓ |

**Verdict: ENTITY** ✓

### Example 6: Location

| Test | Answer | Result |
|------|--------|--------|
| Can a Location exist without relationships? | YES - "123 Main Street exists even if no one lives there" | ✓ |
| Can you define "Location" without another entity? | YES - "A physical place with coordinates/address" | ✓ |
| Is Location where influence stops? | YES - Physical anchor point | ✓ |
| Do other things reference Location? | YES - Residences, headquarters, meeting places | ✓ |

**Verdict: ENTITY** ✓

### Example 7: Orphan Data (Scraped Profile)

| Test | Answer | Result |
|------|--------|--------|
| Can Orphan Data exist without relationships? | Currently yes, but this is temporary | ─ |
| Can you define it without another entity? | It's ABOUT an entity we haven't linked yet | ─ |
| Is it where influence stops? | NO - It should be attached to a real entity | ✗ |
| Is the "independence" inherent or circumstantial? | CIRCUMSTANTIAL - data awaiting linkage | ─ |

**Verdict: ORPHAN DATA** (Temporary storage, not a true entity type)

---

## Summary Classification

### True Entities (Ontologically Independent)

| Entity | Independence Proof |
|--------|-------------------|
| **Person** | Exists regardless of digital presence or affiliations |
| **Organization** | Exists even with no employees or assets |
| **Platform** | Exists as a concept even with no users or owner |
| **Location** | Exists as physical place regardless of occupancy |
| **Group** | Exists even with zero current members |
| **Government** | Exists as institution independent of officials |
| **Sock Puppet** | Fictional persona exists as defined identity |

### Dependent Data (Ontologically Dependent)

| Data | Dependency Proof | Modeling |
|------|-----------------|----------|
| **Account** | INHERENTLY requires Platform to exist | Relationship: HAS_ACCOUNT_ON |
| **Content** | INHERENTLY requires Platform + Author | Properties on relationships |

### Orphan Data (Circumstantially Unlinked)

| Data | Circumstance | Modeling |
|------|--------------|----------|
| **Unlinked Profile** | Awaiting Person entity linkage | OrphanData node (temporary) |
| **Scraped Data** | Awaiting entity identification | OrphanData node (temporary) |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│           ONTOLOGICAL INDEPENDENCE TEST (Quick Check)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Ask: "Can X exist and be defined without ANY other entity?"    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ YES, ALWAYS → ENTITY (create Node)                      │   │
│  │                                                         │   │
│  │ NO, NEVER   → DEPENDENT DATA (use Relationship/Property)│   │
│  │                                                         │   │
│  │ YES, BUT... → Check: Is independence inherent or        │   │
│  │              circumstantial?                            │   │
│  │              • Inherent independence → ENTITY           │   │
│  │              • Circumstantial (missing link) → ORPHAN   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Examples:                                                      │
│  • "Can a Person exist without a Platform?" → YES → ENTITY     │
│  • "Can an Account exist without a Platform?" → NO → DEPENDENT │
│  • "Does this data exist without a link?" → Missing → ORPHAN   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Using This Test for Future Entity Proposals

When someone proposes a new entity type for basset-hound:

1. **Apply the Primary Question**: "Can this thing exist and be clearly defined without requiring ANY relationship to another entity?"

2. **Run the Secondary Tests**: Standalone, Definition, Pipeline, Reference, Query

3. **Check for False Independence**: Is it truly independent, or just orphan data?

4. **Document the Analysis**: Add to findings with test results

5. **If ENTITY**: Create Node type with appropriate labels and properties

6. **If DEPENDENT**: Model as Relationship type or Property on existing relationships

7. **If ORPHAN**: Use OrphanData temporary storage until entity linkage

---

## Sources

- [Stanford Encyclopedia of Philosophy - Ontological Dependence](https://plato.stanford.edu/entries/dependence/)
- [Stanford Encyclopedia of Philosophy - Substance](https://plato.stanford.edu/entries/substance/)
- [Komprise - Orphan Data Definition](https://www.komprise.com/glossary_terms/orphan-data/)
- [Database.guide - Orphan Records](https://database.guide/what-is-an-orphan-record/)
- [BigBear.ai - Property Graphs](https://bigbear.ai/blog/property-graphs-is-it-a-node-a-relationship-or-a-property/)
- [Neo4j - Graph Modeling Guidelines](https://neo4j.com/developer/guide-data-modeling/)
