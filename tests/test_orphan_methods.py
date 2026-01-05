"""
Test script for orphan data methods in Neo4jHandler
"""
from neo4j_handler import Neo4jHandler
from datetime import datetime

def test_orphan_methods():
    """Test all orphan data methods"""
    handler = Neo4jHandler()

    # Create a test project if needed
    projects = handler.get_all_projects()
    if projects:
        project_id = projects[0]["safe_name"]
        print(f"Using existing project: {project_id}")
    else:
        project = handler.create_project("Test Project", "test_project")
        project_id = project["safe_name"]
        print(f"Created test project: {project_id}")

    print("\n=== Testing Orphan Data Methods ===\n")

    # Test 1: Create orphan data
    print("1. Creating orphan data...")
    orphan1 = handler.create_orphan_data(project_id, {
        "identifier_type": "email",
        "identifier_value": "john.doe@example.com",
        "source_file": "contacts.csv",
        "source_location": "row 5",
        "context": "Found in imported contacts",
        "tags": ["import", "unmatched"],
        "notes": "Needs manual review",
        "metadata": {"confidence": 0.8, "source": "csv_import"}
    })
    print(f"   Created orphan: {orphan1['id']}")
    print(f"   Identifier: {orphan1['identifier_value']}")
    print(f"   Tags: {orphan1['tags']}")
    print(f"   Metadata: {orphan1.get('metadata')}")

    # Test 2: Get orphan data
    print("\n2. Getting orphan data by ID...")
    retrieved = handler.get_orphan_data(project_id, orphan1['id'])
    print(f"   Retrieved: {retrieved['identifier_value']}")
    print(f"   Linked: {retrieved['linked']}")

    # Test 3: Create more orphans for testing
    print("\n3. Creating additional orphans...")
    orphan2 = handler.create_orphan_data(project_id, {
        "identifier_type": "phone",
        "identifier_value": "+1-555-1234",
        "source_file": "contacts.csv",
        "tags": ["import"],
    })
    orphan3 = handler.create_orphan_data(project_id, {
        "identifier_type": "email",
        "identifier_value": "duplicate@example.com",
        "source_file": "file1.csv",
        "tags": ["duplicate"],
    })
    orphan4 = handler.create_orphan_data(project_id, {
        "identifier_type": "email",
        "identifier_value": "duplicate@example.com",
        "source_file": "file2.csv",
        "tags": ["duplicate"],
    })
    print(f"   Created {3} additional orphans")

    # Test 4: List orphan data with pagination
    print("\n4. Listing orphan data (paginated)...")
    orphans = handler.list_orphan_data(project_id, limit=10, offset=0)
    print(f"   Found {len(orphans)} orphans")
    for o in orphans:
        print(f"   - {o['identifier_type']}: {o['identifier_value']}")

    # Test 5: List with filters
    print("\n5. Listing orphans with filters (identifier_type=email)...")
    email_orphans = handler.list_orphan_data(project_id,
        filters={"identifier_type": "email"}, limit=10)
    print(f"   Found {len(email_orphans)} email orphans")

    print("\n6. Listing orphans with tag filter (tags=['import'])...")
    import_orphans = handler.list_orphan_data(project_id,
        filters={"tags": ["import"]}, limit=10)
    print(f"   Found {len(import_orphans)} orphans with 'import' tag")

    # Test 7: Count orphan data
    print("\n7. Counting orphan data...")
    total_count = handler.count_orphan_data(project_id)
    print(f"   Total orphans: {total_count}")
    email_count = handler.count_orphan_data(project_id,
        filters={"identifier_type": "email"})
    print(f"   Email orphans: {email_count}")

    # Test 8: Update orphan data
    print("\n8. Updating orphan data...")
    updated = handler.update_orphan_data(project_id, orphan1['id'], {
        "notes": "Reviewed - ready for linking",
        "tags": ["import", "reviewed"]
    })
    print(f"   Updated notes: {updated['notes']}")
    print(f"   Updated tags: {updated['tags']}")

    # Test 9: Search orphan data
    print("\n9. Searching orphan data...")
    search_results = handler.search_orphan_data(project_id, "john")
    print(f"   Found {len(search_results)} results for 'john'")
    for result in search_results:
        print(f"   - {result['identifier_value']}")

    # Test 10: Find duplicates
    print("\n10. Finding duplicate orphans...")
    duplicates = handler.find_duplicate_orphans(project_id)
    print(f"   Found {len(duplicates)} duplicate groups")
    for dup in duplicates:
        print(f"   - {dup['identifier_value']}: {dup['count']} occurrences")

    # Test 11: Link orphan to entity (if entities exist)
    print("\n11. Testing orphan-to-entity linking...")
    people = handler.get_all_people(project_id)
    if people:
        person_id = people[0]["id"]
        link_result = handler.link_orphan_to_entity(orphan1['id'], person_id)
        if link_result:
            print(f"   Linked orphan {link_result['orphan_id']} to entity {link_result['entity_id']}")
            print(f"   Linked at: {link_result['linked_at']}")

            # Verify linked status
            linked_orphan = handler.get_orphan_data(project_id, orphan1['id'])
            print(f"   Orphan linked status: {linked_orphan['linked']}")
            if 'linked_entity_ids' in linked_orphan:
                print(f"   Linked to entities: {linked_orphan['linked_entity_ids']}")
        else:
            print("   Failed to create link")
    else:
        print("   No entities available for linking test")
        # Create a test person
        test_person = handler.create_person(project_id, {"profile": {}})
        if test_person:
            person_id = test_person["id"]
            link_result = handler.link_orphan_to_entity(orphan1['id'], person_id)
            if link_result:
                print(f"   Linked orphan to newly created entity {person_id}")

    # Test 12: Delete orphan data
    print("\n12. Deleting orphan data...")
    deleted = handler.delete_orphan_data(project_id, orphan2['id'])
    print(f"   Delete result: {deleted}")

    # Verify deletion
    deleted_orphan = handler.get_orphan_data(project_id, orphan2['id'])
    print(f"   Orphan exists after delete: {deleted_orphan is not None}")

    print("\n=== All Tests Completed ===")

    handler.close()

if __name__ == "__main__":
    test_orphan_methods()
