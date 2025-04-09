
Setup the python venv

```
python3 -m venv venv
```

```
source venv/bin/activate
```


TODO

## Phase 1 - Manage People Data

 - [ ] setup data ingest template - data.yaml to give a reference for data categories and what to expect when populating the dashboard
 - [ ] add email, username, and password to social media fields (select email from previous emails)
 - [ ] add "events" data fields with event name, date range, location and comments to tie people to an event
 	- [ ] for simplicity of data storage - treat people, organizations, and events as the same type of entity
  	- [ ] able to tag people to people, people to organizations, and people to events
   	- [ ] simply add a person/entity and then fill in same template of information
   	- [ ] add more specific fields for organizations and events
   	- [ ] add known locations and times
   		- [ ] when a new location is know, the newly second most recent location date range updates from "present" to the current date because person has moved
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


I am looking fix my current code for a flask app and remove code that will become obsolete. do not respond yet I will provide the error I am facing in my current code. I will always have a default data_config.yaml file, no need to add into the code a default config. 
I have the following files for a flask app, I want to add a feature that provides a template for how profile information for people is treated. I want to divide a profile into sections of information. For example, the names, emails, dates of birth, I want to have a data_config.yaml that names and structures sections of data. This way I can have different sections of data but standardize how it is all rendered. If a field is an email, it will have a hyperlink in the html, a date will have a calender to select from when editing user info, and a string will simply be treated as a normal string. notice how different social media sites's data is structured differently? this is to provide a template for the app to generate a person's profile based on how the user wants the data to be treated in the system. Please add this feature and remove code that will become obsolete. Remember that people can have multiple of the same thing, so you should keep the feature to "add another" or "remove" for sections and subsections, essentially in the  "core" section, the user selects "add another" and then is prompted to select from name, date of birth, and email. if in the social section, they are prompted to add a linkedin or twitter. From this template multiple sections are generated, but only sections with fields with entered data (only show fields that have information). Then when editing a profile information, strings are left alone, emails are given email hyperlinks, and urls are given hyperlinks. This should keep profiles simple and make profile structuring easier for different users with different needs.
    core
        name: string
        date of birth: date
        email: email
    social
        linkedin: url
            login: email
            pass: string
            username: string
            url: url
        twitter: url
            user: string
            password: string
            email: email


I want to add a feature where you can add connections between people, but structure it similar to a social media tag. At the bottom of someone's profile, have block of buttons (instead of a vertical list which would make the page incredibly long) where the user of the app can tag another person in the people manager. then I want the following logic in the tag feature:

logic: if person1 is related to person2 and person2 is related to person3, then person3 is related to person1

feature: when person1 is tagged in person2's profile, update all other connections between people in the app recursively.

(transitive relationship logic)