
Setup the python venv

```
python3 -m venv venv
```

```
source venv/bin/activate
```


TODO

## Phase 1 - Manage People Data


 - [ ] able to tag people to people, people to organizations, and people to events
 - [ ] profile pic, default profile pic
 - [ ] connected people
	- [ ] list / table / tags of people in profile
	- [ ] list / table / tags of other related people by hopping in profile
	- [ ] if person1 is related to person2 and person2 is related to person3, then person3 is related to person1
	- [ ] keep track of how many hops between a person
 - [ ] add files to an individual and relevant comments for each file
	- [ ] when delete person, choice to keep files
		- [ ] choice which files to keep (can choose all)
		- [ ] if files not chosen to keep, delete files
		- [ ] if chose to keep files, prompt with path to folder containgin files
 - [ ] button generate report (simply show information) in markdown, button for pdf
 	- [ ] Have report templates
  		- [ ] modular/selectable 
  		- [ ] default - simple raw	
 - [ ] fast api for automating people adding/editing/deleting data import and export
 - [ ] neo4j (dockerized)
 - [ ] graphical/visual connections
	- [ ] show first hop connections on a person's profile
	- [ ] "Graph Connections" button to show recursive hop connetions on a new page

## Phase 2 - Performing Background Tasks
 - [ ] Conduct OSINT
 	- [ ] search multiple search engines at once
  		- [ ] clearnet
    		- [ ] tor (must be inside tor browser) 	 
 	- [ ] make requests to websites to verify social media handles / links
  		- [ ] add custome social media urls to profile, user link prepend, username, user link append  	
        - [ ] automate google dorks
	- [ ] automate search results on public records

## Phase 3 - Manage Fake People?
 - [ ] Generate Fake People With Information
 	- [ ] Create Email Account
  	- [ ] Smokescreen Activity / Normalize activity
   		- [ ] Subscribe to newsletters
	- [ ] generate passwords
 	- [ ] automatically make social media accounts? 


 - [ ] recently opened projects on index.html


I want to add a feature where you can add connections between people, but structure it similar to a social media tag. From the search on the side bar of the dashboard, i want results to have a tag icon on the right side, if a profile is not pulle up the tags are not visible, if the user is viewing someone's profile, the tags are visible. the user simply has to search in the search bar and the results pop up, from ther the user can click the tag button to tag the resulting person to the current profile person. Store all people tagged by the person's profile in a list using the update people and edit people and add people forms or whatever is the best way for the current code to get the list of tags into the JSON file. At the bottom of the current person's profile, have a section that is a grid of buttons, these buttons will be rendered from the list of tags of the person's profile. when one of those buttons is clicked, it takes the user to the new person's profile. if the user would like to remove a tag, they can choose to edit the profile, scroll down to an auto populated list, and click remove for an item on that list. All tags on a profile should have the tagged person's id under the same person's display name so that the user can know who is who.


I now want to add the functionality to create a network of people based on who they tag. I want to use transitive relationship logic - if person1 is related to person2 and person2 is related to person3, then person3 is related to person1. I will consider the people tagged on a person's profile (the subject) as 1 hop from the subject, then the people tagged on the profiles of the people tagged on the subject's profile will be considered 2 hops from the subject. I want to keep track of the routes and combinations of hops between everybody, essentially performing recursion. I want to make a new page called "tagged.html" where I want to have a dynamic, visual graph of all the connections between all the people.

logic: if person1 is related to person2 and person2 is related to person3, then person3 is related to person1

feature: when person1 is tagged in person2's profile, update all other connections between people in the app recursively.
