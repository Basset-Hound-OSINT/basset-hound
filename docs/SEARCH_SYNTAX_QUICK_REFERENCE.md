# Advanced Search - Quick Reference Guide

## Basic Syntax

### Simple Search
```
John Doe
```
Searches all fields for "John Doe"

### Field-Specific Search
```
field:value
```
Searches only in the specified field

**Examples:**
```
email:john@example.com
name:John
phone:555-1234
status:active
```

## Boolean Operators

### AND Operator
Both conditions must match
```
name:John AND email:*@gmail.com
```

### OR Operator
At least one condition must match
```
email:john@example.com OR phone:555-1234
```

### NOT Operator
Negates the following condition
```
tag:customer AND NOT status:inactive
```

## Wildcards

### Asterisk (*) - Multiple Characters
Matches zero or more characters
```
john*              # Matches: john, johnny, johnson
*@gmail.com        # Matches any email at gmail.com
email:*test*       # Matches emails containing "test"
```

### Question Mark (?) - Single Character
Matches exactly one character
```
j?hn               # Matches: john, jahn
phone:555-???4     # Matches: 555-1234, 555-9994
```

## Phrase Search

### Exact Phrase
Use quotes for exact phrase matching
```
"John Smith"       # Exact match for "John Smith"
```

### Field-Specific Phrase
```
name:"John Doe"    # Exact phrase in name field
```

## Grouping

### Parentheses
Group conditions for complex logic
```
(name:John OR name:Jane) AND status:active
```

### Nested Groups
```
((A OR B) AND C) OR (D AND E)
```

## Operator Precedence

1. **NOT** (highest)
2. **AND**
3. **OR** (lowest)

**Example:**
```
A OR B AND NOT C
```
Evaluates as: `A OR (B AND (NOT C))`

**Use parentheses to override:**
```
(A OR B) AND NOT C
```

## Common Query Patterns

### Email Searches
```
# Exact email
email:john@example.com

# Gmail users
email:*@gmail.com

# Multiple domains
email:*@gmail.com OR email:*@yahoo.com

# Specific user across domains
email:john*
```

### Name Searches
```
# Exact name
name:"John Doe"

# First name only
name:John

# Wildcard name
name:J*

# Alternative names
name:John OR name:Jonathan
```

### Status Filters
```
# Active only
status:active

# Active or pending
status:active OR status:pending

# Exclude archived
NOT status:archived

# Active but not deleted
status:active AND NOT deleted:true
```

### Phone Number Searches
```
# Area code
phone:555*

# Multiple area codes
phone:555* OR phone:777* OR phone:888*

# Partial number
phone:*1234
```

### Combined Criteria
```
# Active Gmail users
email:*@gmail.com AND status:active

# Suspects not cleared
tag:suspect AND NOT status:cleared

# Multiple tags
(tag:suspect OR tag:poi) AND status:active
```

## Investigation Workflows

### Find All Company Employees
```
email:*@company.com
```

### Find Active Suspects
```
tag:suspect AND status:active AND NOT cleared:true
```

### Find Contacts by Phone Prefix
```
phone:555* OR phone:777*
```

### Find People in City with Specific Tag
```
city:Boston AND (tag:suspect OR tag:witness)
```

### Exclude Archived Records
```
name:John AND NOT archived:true
```

### Complex Investigation Query
```
(email:*@suspicious-domain.com OR phone:555-0100*)
AND (tag:suspect OR tag:person_of_interest)
AND NOT status:cleared
```

## Field Paths

Fields use dot notation for nested access:
```
core.name
core.email
core.contact.phone
social.linkedin
tags.status
```

**Example:**
```
core.email:*@gmail.com AND tags.status:active
```

## Tips and Best Practices

### 1. Start Simple
Begin with simple queries and add complexity:
```
# Start with:
name:John

# Then add:
name:John AND email:*@gmail.com

# Finally:
(name:John OR name:Jonathan) AND email:*@gmail.com AND NOT status:archived
```

### 2. Use Field-Specific Searches
Field searches are faster and more accurate:
```
# Better:
email:john@example.com

# Slower:
john@example.com
```

### 3. Place Restrictive Conditions First
```
# Better (fewer results to process):
status:active AND name:John

# Works but slower:
name:John AND status:active
```

### 4. Avoid Excessive Wildcards
```
# Good:
john*

# Slow:
*john*

# Very slow:
*j*o*h*n*
```

### 5. Use Parentheses for Clarity
```
# Clear:
(A OR B) AND (C OR D)

# Confusing:
A OR B AND C OR D
```

### 6. Test Queries Incrementally
Build complex queries step by step:
```
# Step 1:
email:*@gmail.com

# Step 2:
email:*@gmail.com AND status:active

# Step 3:
(email:*@gmail.com OR email:*@yahoo.com) AND status:active
```

## Common Mistakes

### 1. Forgetting Quotes for Phrases
```
# Wrong:
name:John Doe

# Right:
name:"John Doe"
```

### 2. Incorrect Wildcard Placement
```
# Wrong (looking for literal asterisk):
email:*gmail.com

# Right:
email:*@gmail.com
```

### 3. Missing Field Separator
```
# Wrong:
emailjohn@example.com

# Right:
email:john@example.com
```

### 4. Unbalanced Parentheses
```
# Wrong:
(name:John AND email:test

# Right:
(name:John AND email:test)
```

## API Endpoints

### Get Syntax Help
```bash
GET /api/v1/search/syntax-help
```

### Simple Search
```bash
GET /api/v1/projects/{project_id}/search?q=John+Doe
```

### Advanced Search
```bash
GET /api/v1/projects/{project_id}/search/advanced?q=email:john*+AND+NOT+status:archived
```

### Get Searchable Fields
```bash
GET /api/v1/search/fields
```

## Example API Calls

### cURL Examples

```bash
# Simple search
curl "http://localhost:8000/api/v1/projects/my-project/search?q=John"

# Advanced search with AND
curl "http://localhost:8000/api/v1/projects/my-project/search/advanced?q=name:John+AND+email:*@gmail.com"

# Advanced search with OR
curl "http://localhost:8000/api/v1/projects/my-project/search/advanced?q=phone:555*+OR+phone:777*"

# Complex query
curl "http://localhost:8000/api/v1/projects/my-project/search/advanced?q=(tag:suspect+OR+tag:poi)+AND+NOT+status:cleared"

# Get syntax help
curl "http://localhost:8000/api/v1/search/syntax-help"
```

### Python Examples

```python
from api.services.search_service import SearchService, SearchQuery

# Simple search
query = SearchQuery(query="John Doe", project_id="my-project")
results, total = await service.search(query)

# Advanced search
query = SearchQuery(
    query="email:*@gmail.com AND status:active",
    project_id="my-project",
    advanced=True
)
results, total = await service.search(query)

# Parse and validate query
parsed = service.parse_advanced_query("name:John AND email:test")
if parsed.error:
    print(f"Error: {parsed.error}")
```

## Troubleshooting

### No Results Found
1. Check field names with `/api/v1/search/fields`
2. Verify wildcards are correct
3. Try simpler query first
4. Check for typos in field names

### Syntax Error
1. Check for unbalanced parentheses
2. Verify quotes are closed
3. Review syntax help
4. Test simpler version of query

### Slow Performance
1. Use field-specific searches
2. Reduce number of wildcards
3. Add more specific conditions
4. Use AND to narrow results

## Quick Reference Table

| Feature | Syntax | Example |
|---------|--------|---------|
| Field search | `field:value` | `email:john@example.com` |
| AND operator | `A AND B` | `name:John AND status:active` |
| OR operator | `A OR B` | `email:test OR phone:555*` |
| NOT operator | `NOT A` | `NOT status:archived` |
| Phrase search | `"phrase"` | `"John Doe"` |
| Wildcard (multi) | `*` | `john*`, `*@gmail.com` |
| Wildcard (single) | `?` | `j?hn` |
| Grouping | `(...)` | `(A OR B) AND C` |

## Getting Help

- **Syntax Help API**: `/api/v1/search/syntax-help`
- **Searchable Fields**: `/api/v1/search/fields`
- **Full Documentation**: See `ADVANCED_SEARCH_IMPLEMENTATION.md`
- **Test Examples**: See `tests/test_advanced_search.py`
