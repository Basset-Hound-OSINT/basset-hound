
Setup the python venv

```
python3 -m venv venv
```

```
source venv/bin/activate
```


TODO

## Phase 1 - Manage People Data
 - [ ] exit button next to but before "add person" to return to index.html to select a project to open
 - [ ] unique id
 	- [ ] check current list of people
	- [ ] check project folder for folders of same string name (see adding files to individuals)
 - [ ] keep track of age of person's account with basset-hound system - when they were added to the system
 - [ ] add email, username, and password to social media fields (select email from previous emails)
 - [ ] profile pic, default profile pic
 - [ ] postgresql (dockerized)
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
 - [ ] graphical connections
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


I have the following code for a flask project. I want all people in the manager to have unique ids attatched to their profile, like a docker container, and make sure that no id that is generated is already in use, display the id below the person's name in the side bar and then under their name in their profile. simply show me what code needs to be added and where in what files so you don't have to rewrite the entire files



I want to add a feature where you can add connections between people, but structure it similar to a social media tag. At the bottom of someone's profile, have block of buttons (instead of a vertical list which would make the page incredibly long) where the user of the app can tag another person in the people manager. then I want the following logic in the tag feature:

logic: if person1 is related to person2 and person2 is related to person3, then person3 is related to person1

feature: when person1 is tagged in person2's profile, update all other connections between people in the app recursively.

