TODO

## Phase 1 - Manage People Data

 - [ ] able to tag people to people, people to organizations, and people to events
 - [ ] connected people
	- [ ] list / table / tags of people in profile
	- [ ] list / table / tags of other related people by hopping in profile
	- [ ] if person1 is related to person2 and person2 is related to person3, then person3 is related to person1
	- [ ] keep track of how many hops between a person
 - [ ] when delete person, choice to keep files
	- [ ] choice which files to keep (can choose all)
	- [ ] if files not chosen to keep, delete files
	- [ ] if chose to keep files
		- [ ] zip user files and append user's display name to zip (in a safe format for fs)
		- [ ] prompt with path to folder containing files
 - [ ] button to generate report (simply show information) in markdown, button for pdf
 	- [ ] Have report templates
  		- [ ] modular/selectable 
  		- [ ] default - simple raw	
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

I have the following flask app, I want to add a feature where i can "tag" another person from a person's profile so that I can make a connection to that person. effectively, i want to have a list of tagged people at the bottom of a person's profile where their display names and ids are shown for me to be able to copy. I want to have this tag feature when i add people and edit people's information, but be separate from the concept of my data configuration file. I would then want a list of tagged people attatched with their ids stored in the project json. for example I would want to have at the bottom of a user's profile:

Tagged People

name: "harry"
id: "123ntni23u3"

name: "joel"
id: "927ifia7837"

I want to leverage the list of people on the side bar. basically, make a tag button in the person's profile next to the edit and delete buttons. when it is clicked, the user should able to select from the scrollable list of users from the side bar - turn it into a checked list - of people of who to tag, the people that get selected are then added to the tagged people in the JSON for that person and then rendered on the dashboard in their profile. One problem you might run into is that the create person form (add person) and edit person forms may overwrite tagged people data. If you can, store all people tagged by the person's profile in a list using the update people and edit people and add people forms or whatever is the best way for the current code to get the list of tags into the JSON file. At the bottom of the current person's profile, have a section that is a grid of buttons, these buttons will be rendered from the list of tags of the person's profile. when one of those buttons is clicked, it takes the user to the new person's profile. if the user would like to remove a tag, they can choose to edit the profile, scroll down to an auto populated list, and click remove for an item on that list. All tags on a profile should have the tagged person's id under the same person's display name so that the user can know who is who.







I now want to add the functionality to create a network of people based on who they tag and render this on a new page "map.html". I want make a button on a user's profile next to "edit" and "delete" labeld "map". when clicked, this button will open a new tab with the url of the map page, load the data from the person's profile from which the map button was clicked, and then render a recursive, visual network of connections stemming from this individual. I want to use transitive relationship logic - if person1 is related to person2 and person2 is related to person3, then person3 is related to person1. I will consider the people tagged on a person's profile (the subject) as 1 hop from the subject, then the people tagged on the profiles of the people tagged on the subject's profile will be considered 2 hops from the subject. I want to keep track of the routes and combinations of hops between everybody, essentially performing recursion. I want to make a new page called "tagged.html" where I want to have a dynamic, visual graph of all the connections between all the people.

logic: if person1 is related to person2 and person2 is related to person3, then person3 is related to person1

feature: when person1 is tagged in person2's profile, update all other connections between people in the app recursively.



