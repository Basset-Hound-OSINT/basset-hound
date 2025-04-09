
Setup the python venv

```
python3 -m venv venv
```

```
source venv/bin/activate
```


TODO

## Phase 1 - Manage People Data

 - [ ] add "events" data fields with event name, date range, location and comments to tie people to an event
 	- [ ] for simplicity of data storage - treat people, organizations, and events as the same type of entity
  	- [ ] able to tag people to people, people to organizations, and people to events
 - [ ] profile pic, default profile pic
 - [ ] connected people
	- [ ] list / table / tags of people in profile
	- [ ] list / table / tags of other related people by hopping in profile
	- [ ] if person1 is related to person2 and person2 is related to person3, then person3 is related to person1
	- [ ] keep track of how many hops between a person
 - [ ] add comments to individual - big text area to past stuff
 - [ ] add files to an individual and relevant comments for each file
	- [ ] make a folder for the project, then make a folder for each person based on unique id, then store files in each person's folder
	- [ ] when delete person, choice to keep files
		- [ ] choice which files to keep (can choose all)
		- [ ] if files not chosen to keep, delete files
		- [ ] if chose to keep files, prompt with path to folder containing files
	- [ ] only show a list of file names (hyperlinks) with comments on profile
 - [ ] button generate report (simply show information) in markdown, button for pdf
 	- [ ] Have report templates
  		- [ ] modular/selectable 
  		- [ ] default - simple raw	
 - [ ] fast api for automating people adding/editing/deleting data import and export
 - [ ] postgresql (dockerized)
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

## Phase 3 - Manage Fake People
 - [ ] Generate Fake People With Information
 	- [ ] Create Email Account
  	- [ ] Smokescreen Activity / Normalize activity
   		- [ ] Subscribe to newsletters
	- [ ] generate passwords
 	- [ ] automatically make social media accounts? 


 - [ ] recently opened projects on index.html


I want to add a feature where you can add connections between people, but structure it similar to a social media tag. At the bottom of someone's profile, have block of buttons (instead of a vertical list which would make the page incredibly long) where the user of the app can tag another person in the people manager. then I want the following logic in the tag feature:

logic: if person1 is related to person2 and person2 is related to person3, then person3 is related to person1

feature: when person1 is tagged in person2's profile, update all other connections between people in the app recursively.

(transitive relationship logic)
