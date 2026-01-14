# Entity Ontology Research for basset-hound

**Date:** 2026-01-14
**Topic:** What Makes Something an Entity vs. Data/Relationship
**Status:** Research Complete, Design Recommendations Included

---

## The Core Question

> "Entities are what are trying to be related... data is how entities are related, by sharing data... different types of entities can have different relationships with other entities because they have different relationships with different data."

This intuition is correct and aligns with established knowledge representation theory.

---

## Key Concepts from Research

### 1. Entity Definition (Ontological)

From [Stanford's Ontology Development 101](https://protege.stanford.edu/publications/ontology_development/ontology101.pdf):

> "Ontology is the study or concern about what kinds of things exist - what entities or 'things' there are in the universe."

From [Wikipedia - Ontology Components](https://en.wikipedia.org/wiki/Ontology_components):

> "Individuals (instances) are the basic, 'ground level' components of an ontology. The individuals in an ontology may include concrete objects such as people, animals, tables, automobiles, molecules, and planets, as well as abstract individuals such as numbers and words."

**Key insight:** An entity is something that:
- Has **independent existence** (can be referred to on its own)
- Has **identity** (can be distinguished from other entities)
- Can **participate in relationships** with other entities
- Has **attributes** that describe it

### 2. Relationship vs. Entity Decision

From [BigBear.ai - Property Graphs: Node, Relationship, or Property?](https://bigbear.ai/blog/property-graphs-is-it-a-node-a-relationship-or-a-property/):

> "The answer to 'Should it be a Node, a Relationship, or a Property?' depends on the kinds of queries you want to run against your model."

From [Neo4j Graph Modeling Guidelines](https://neo4j.com/developer/guide-data-modeling/):

> "Nodes and Labels are the best way to access a graph when querying and represent distinct entities. Relationships are powerful ways to access different types of nodes at the same time, move through the graph, and filter data."

**The critical test:** If something is **referenced by other things**, it should be a node. If it only **connects** two things, it's a relationship.

### 3. The Type-Token Distinction

From [Wikipedia - Ontology (information science)](https://en.wikipedia.org/wiki/Ontology_(information_science)):

> "According to the type-token distinction, the ontology is divided into individuals, who are real world objects or events, and types or classes, who are sets of real world objects."

Example:
- **Class (Type):** "Platform" - the concept of an online platform
- **Instance (Token):** "Facebook" - a specific platform

---

## Applied to basset-hound

### What Makes Something an Entity in basset-hound?

**The Ontological Independence Test:**

An **entity** in basset-hound is something that can **exist and be clearly defined without requiring a relationship to another entity**.

> "An entity is where the pipeline of influence stops - something that can stand alone by itself and not need any relationship with another entity to be clearly defined."

**Examples:**
- **Platform** is an entity: Facebook exists as a platform even if no company owns it and no users have accounts. "A platform can simply just be a platform, a place where people interact and content is shared."
- **Location** is an entity: "123 Main Street" exists as a location even if no person lives there and no company is headquartered there.
- **Group** is an entity: A group can exist with 0 members - "there can be 0 people in a group if all the people left."
- **Person** is an entity: A person exists independently of their accounts, employers, or relationships.

**Counter-examples:**
- **Content** is NOT an entity: A post/message cannot be clearly defined without knowing which platform hosts it. Content requires context.
- **Account** is NOT an entity: An account cannot exist without a platform to host it. "An account would need to be defined by a platform that it is hosted on."

### The Entity Test (Updated)

The primary question: **Can this thing exist and be meaningful without ANY relationship to another entity?**

| Question | If YES | If NO |
|----------|--------|-------|
| Can it exist without relationships? | Entity | Dependent data |
| Can you define it without referencing another entity? | Entity | Dependent data |
| Is it where the "pipeline of influence" stops? | Entity | Pass-through data |

### Dependent Data (Not Entities)

Some things that seem like entities are actually **dependent data** - they require another entity to exist:

| Dependent Data | Requires | Modeled As |
|----------------|----------|------------|
| Account | Platform | Relationship (HAS_ACCOUNT_ON) with properties |
| Content | Platform (at minimum) | Relationship or property, not independent entity |
| Orphan Data | Eventually linked to entity | Temporary storage until entity attachment |

**Note on Orphan Data:** Orphan data is data that hasn't been attached to an entity YET. It's not an entity itself - it's data waiting to be linked. Once linked, it becomes properties/relationships on an actual entity.

**Important Distinction - Orphan vs Ontologically Dependent**:

| Concept | Nature | Example |
|---------|--------|---------|
| **Orphan Data** | *Temporary state* - data awaiting linkage | Scraped email not yet linked to Person |
| **Ontologically Dependent** | *Inherent property* - cannot exist without another entity | Account (always needs Platform) |

Orphan data COULD be linked to an existing entity type (we just haven't done it yet). Ontologically dependent data CANNOT exist without its parent entity (by definition).

For the formal Ontological Independence Test framework, see: [ONTOLOGICAL-INDEPENDENCE-TEST-2026-01-14.md](ONTOLOGICAL-INDEPENDENCE-TEST-2026-01-14.md)

---

## basset-hound Entity Classification

### True Entities (Pass the Ontological Independence Test)

| Entity Type | Why It's an Entity (Can Exist Independently) |
|-------------|---------------------------------------------|
| **Person** | A person exists regardless of accounts, employers, or relationships |
| **Organization** | A company exists even if no one works there and it owns nothing |
| **Platform** | "A platform can simply just be a platform" - exists without owners or users |
| **Location** | An address exists even if no one lives there or uses it |
| **Government** | A government entity exists independently of its relationships |
| **Group** | "There can be 0 people in a group if all the people left" |
| **Sock Puppet** | The fictional persona exists as a defined identity, independent of where it's used |
| **Unknown** | Placeholder for unclassified entities - still independent |

### NOT Entities (Dependent Data)

| Concept | Why It's NOT an Entity | How to Model |
|---------|------------------------|--------------|
| **Account** | Cannot exist without a Platform to host it | Relationship: HAS_ACCOUNT_ON with properties (username, profile_url, etc.) |
| **Content** | Cannot be defined without knowing which Platform hosts it | Relationship properties or nested data on HAS_ACCOUNT_ON |
| **Orphan Data** | Data waiting to be linked - not independently meaningful | Temporary storage (OrphanData node) until attached to real entity |

### Relationships (Connections Between Entities)

| Relationship | Connects | Properties |
|--------------|----------|------------|
| **HAS_ACCOUNT_ON** | Person/SockPuppet → Platform | username, profile_url, display_name, password_ref, verified, platform-specific fields |
| **OWNS** | Person/Org → Org/Platform/Location | since, ownership_type, percentage |
| **WORKS_AT** | Person → Organization | since, until, role, department |
| **LOCATED_IN** | Any Entity → Location | since, until, type (residence, headquarters, etc.) |
| **KNOWS** | Person ↔ Person | since, how_met, strength |
| **MEMBER_OF** | Person → Group | since, until, role |
| **CONTROLS** | Org/Person → Sock_Puppet | operator relationship |

### Special Case: Content

Content (posts, messages, articles) is **dependent data** that:
1. Cannot exist without a Platform
2. Cannot exist without an Author (Person/Account)

**Modeling options:**
- **Simple:** Store as properties on HAS_ACCOUNT_ON relationship (list of posts)
- **Complex:** Store as separate nodes linked to both Platform and Person, but acknowledge this is dependent data, not a true entity

**Recommendation:** Keep content as relationship properties for now. If query patterns demand content-centric queries ("find all posts mentioning X"), revisit this decision.

---

## Ownership & Control Model

The key insight from the user:

> "A person owns an account, a platform owns/controls an account, a company owns a platform, a person owns a company..."

This describes **relationship types**, not entity types:

```
OWNERSHIP RELATIONSHIPS:
├── OWNS (legal ownership)
│   ├── Person OWNS Organization
│   ├── Organization OWNS Platform
│   ├── Organization OWNS Organization (subsidiary)
│   └── Person OWNS Location (property)
│
├── CONTROLS (operational control)
│   ├── Platform CONTROLS Content (hosting/moderation)
│   ├── Organization CONTROLS Platform (operational)
│   └── Person CONTROLS Sock_Puppet (operator)
│
├── HAS_ACCOUNT_ON (membership/presence)
│   └── Person HAS_ACCOUNT_ON Platform (with account properties)
│
└── WORKS_AT/MEMBER_OF (affiliation)
    ├── Person WORKS_AT Organization
    └── Person MEMBER_OF Group
```

**Key distinction:**
- **OWNS** implies legal/formal ownership
- **CONTROLS** implies operational control without ownership
- **HAS_ACCOUNT_ON** is a special relationship with rich properties

---

## The Platform Problem (Why Platform Must Be Entity)

The user's insight about platforms:

> "It is simply that some platforms relate so many entities that I had to make a platform entity."

This is correct. Platform must be an entity because:

1. **Multiple persons relate to the same platform** - Can't duplicate platform data on each HAS_ACCOUNT_ON edge
2. **Platform has its own properties** - Name, domain, field schema, owner
3. **Platform can be searched independently** - "Show all entities related to Facebook"
4. **Platform defines schemas** - Field schema varies per platform

If platform were just a property on relationships:
```cypher
// BAD: Platform as property (data duplication, no platform queries)
(:Person)-[:HAS_ACCOUNT {platform: "Facebook", username: "john"}]->(:???)
```

Platform as entity:
```cypher
// GOOD: Platform as entity (single source of truth, queryable)
(:Person)-[:HAS_ACCOUNT_ON {username: "john"}]->(:Platform {name: "Facebook"})
```

---

## Recommended Entity Hierarchy for basset-hound

```
ENTITIES (Nodes)
├── Actors (can take actions)
│   ├── Person
│   ├── Sock_Puppet (fictional actor)
│   └── Group (collective actor)
│
├── Organizations (formal structures)
│   ├── Organization (company, NGO, etc.)
│   └── Government (special organization type)
│
├── Digital Objects (online existence)
│   ├── Platform (where things happen online)
│   └── Content (what is created online)
│
├── Physical Objects
│   └── Location (places)
│
└── Meta Types
    ├── Unknown (unclassified entity)
    └── Custom (user-defined)

FUTURE CANDIDATES:
├── Evidence (if evidence chains become complex)
├── Event (meetings, transactions, incidents)
├── Asset (vehicles, financial instruments)
└── Document (legal docs, certificates)
```

---

## Recommended Relationship Types

```
RELATIONSHIPS (Edges)
├── Ownership/Control
│   ├── OWNS (legal ownership)
│   ├── CONTROLS (operational control)
│   ├── FOUNDED (created the entity)
│   └── SUBSIDIARY_OF (org hierarchy)
│
├── Digital Presence
│   ├── HAS_ACCOUNT_ON (person→platform, with account properties)
│   ├── HOSTS (platform→content)
│   └── POSTED (person→content)
│
├── Social/Professional
│   ├── KNOWS (person↔person)
│   ├── WORKS_AT (person→organization)
│   ├── MEMBER_OF (person→group)
│   └── RELATED_TO (generic relation)
│
├── Location
│   ├── LOCATED_IN (entity→location)
│   ├── HEADQUARTERED_IN (org→location)
│   └── OPERATES_IN (org→location, multiple)
│
├── Content Relations
│   ├── MENTIONED_IN (entity→content)
│   ├── TAGGED_IN (person→content)
│   └── REPLY_TO (content→content)
│
└── Investigation
    ├── SUBJECT_OF (entity→investigation)
    ├── EVIDENCE_FOR (file→entity)
    └── VERIFIED_BY (entity→verification)
```

---

## Key Takeaways

1. **Entities are nouns** - things with independent identity that can be named and searched
2. **Relationships are verbs** - connections that only make sense between entities
3. **Properties are adjectives** - attributes that describe entities or relationships
4. **The query test** - if you need to search for it or reference it from multiple places, it's probably an entity
5. **Platform must be entity** - because multiple entities relate to it and it has its own properties
6. **Account is a relationship** - because it only makes sense connecting Person↔Platform

---

## Sources

- [BigBear.ai - Property Graphs](https://bigbear.ai/blog/property-graphs-is-it-a-node-a-relationship-or-a-property/)
- [Neo4j Graph Database Concepts](https://neo4j.com/docs/getting-started/appendix/graphdb-concepts/)
- [Neo4j Graph Modeling Guidelines](https://neo4j.com/developer/guide-data-modeling/)
- [Linkurious - Graph-based Intelligence Analysis](https://linkurious.com/blog/graph-based-intelligence-analysis/)
- [FalkorDB - Ontologies: Blueprints for Knowledge Graphs](https://www.falkordb.com/blog/understanding-ontologies-knowledge-graph-schemas/)
- [Stanford Protégé - Ontology Development 101](https://protege.stanford.edu/publications/ontology_development/ontology101.pdf)
- [Wikipedia - Ontology Components](https://en.wikipedia.org/wiki/Ontology_components)
- [Wikipedia - Class (Knowledge Representation)](https://en.wikipedia.org/wiki/Class_(knowledge_representation))
