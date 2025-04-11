TODO

## Phase 1 - Manage People Data

 - [ ] hops
	- [ ] list / table / tags of other related people by hopping in profile
	- [ ] if person1 is related to person2 and person2 is related to person3, then person3 is related to person1
	- [ ] keep track of how many hops between a person
 - [ ] fast api for automating people adding/editing/deleting data import and export
 - [ ] neo4j (dockerized)
 - [ ] graphical/visual connections (map.html)
	- [ ] show first hop connections on a person's profile
	- [ ] "Graph Connections" button to show recursive hop connetions on a new page

## Phase 2 - Performing Background Tasks
 - [ ] get permission to open multiple new tabs before trying to open multiple new tabs?
 - [ ] Conduct OSINT (tison.html)
 	- [ ] load user data
 	- [ ] categories of OSINT tools
 		- [ ] osint tools config
 			- [ ] required fields
 			- [ ] non-reqiured fields
 			- [ ] if no fields, ok just take user to url
 			- [ ] if fields, take user to url with populated fields 
 		- [ ] interactive lists of tools
 	- [ ] search multiple search engines at once
  		- [ ] clearnet
    		- [ ] tor (must be inside tor browser) 	 	
       - [ ] automate google dorks, search public records, verify social media

## Phase 3 - Manage Fake People?
 - [ ] Generate Fake People With Full Information
	- [ ] generate passwords
 	- [ ] automatically make social media accounts? 
 	- [ ] Automate Create Email Account?
  	- [ ] Smokescreen Activity / Normalize activity
   		- [ ] Subscribe to newsletters


 - [ ] recently opened projects on index.html


## Helpful prompts to currently work with

```
pip freeze > requirements.txt
```

The folders that you want to mount must exist before starting Docker, otherwise, Neo4j fails to start due to permissions errors.

```bash
docker run \
    --restart always \
    --publish=7474:7474 --publish=7687:7687 \
    --env NEO4J_AUTH=neo4j/neo4jbasset \
    --volume=./projects/data/:/data \
	-d \
	--name=neo4j-basset \
    neo4j:2025.03.0
```

```
http://localhost:7474
```

```bash
docker stop containerid && docker container prune -f
```

https://blog.armbruster-it.de/2019/07/how-to-add-bloom-and-apoc-to-a-neo4j-docker-container/

https://neo4j.com/product/bloom/


I now want to add the functionality to create a network of people based on who they tag and render this on a new page "map.html". I want make a button on a user's profile next to "edit" and "delete" labeld "map". when clicked, this button will open a new tab with the url of the map page (map.html will need to be created), load the data from the person's profile from which the map button was clicked, and then render a recursive, visual network of connections stemming from this individual. I want to use transitive relationship logic - if person1 tags person2 and person2 tags person3, then person3 is related to person1. I will consider the people tagged on a person's profile (the subject) as 1 hop from the subject, then the people tagged on the profiles of the people tagged on the subject's profile will be considered 2 hops from the subject. I want to keep track of the routes and combinations of hops between everybody, essentially performing recursion. I want to make a new page called "tagged.html" where I want to have a dynamic, visual graph of all the connections between all the people.

logic: if person1 is related to person2 and person2 is related to person3, then person3 is related to person1

feature: when person1 is tagged in person2's profile, update all other connections between people in the app recursively.



