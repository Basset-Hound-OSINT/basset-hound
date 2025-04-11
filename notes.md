TODO

## Phase 1 - Manage People Data

 - [ ] able to tag people
   - [ ] edit tags form to search, add, and remove tags instead of modifying dashboard components
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
 - [ ] button to generate report (simply show information) in markdown, or button for pdf
 	- [ ] Have report templates
  		- [ ] modular/selectable 
  		- [ ] default - simple raw	
 - [ ] when downloading a project, if files other than project data, send a zip file.
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

I have the following flask app, I want to add a feature where i can "tag" another person from a person's profile so that I can make a connection to that person. effectively, i want to have a list of tagged people in a "tagged people" section at the bottom of a person's profile where their display names and ids are shown for me to be able to copy. I want to create a "tag" form and create tag-handler.js to help with it. the tag form should have a search bar that searches for a string amongst all users and dynamically updates (just like the search function in the sid bar), then when a user in the results of this search is clicked, they are added to the temporary list of tagged users. for every person on this list, make sure to render their id and name and have a button labled "remove" so that I can remove them from the list if needed before saving changes and making a post request with the list. I might also need to add handler to my flask app for managing a persons tag - I very much want to not delete the person's data from the project JSON, so when adding a person's tagged people, make sure to duplicate the person's json data into memory and simply inject the tagged data as a new section then save it in the project json. From here, make sure to properly render the person's tagged people list on the person's profile. 

example format of the tagged people section.

Tagged People

name: "harry"
id: "123ntni23u3"

name: "joel"
id: "927ifia7837"


this is what i see on the tag form when trying a basic search for something i know is in the project data - basically i am just searching for a string and if that string is found anywhere in a user's data, that users should be displayed in the search results

Tag People for llama man
Search People
No matching people found
Tagged People
No people tagged yet

ubuntu@ubuntu2004:/opt/basset-hound/projects$ cat lol/project_data.json 
{
    "name": "lol",
    "safe_name": "lol",
    "start_date": "2025-04-11",
    "people": [
        {
            "id": "01fff63e0411",
            "created_at": "2025-04-11T03:27:13.763160",
            "profile": {
                "Profile Picture Section": {
                    "profilepicturefile": {
                        "id": "ff4e850bc8d6",
                        "name": "profilepic.png",
                        "path": "ff4e850bc8d6_profilepic.png"
                    }
                },
                "core": {
                    "name": [
                        {
                            "first_name": "llama",
                            "last_name": "man"
                        }
                    ],
                    "summary": [
                        "this is llama man"
                    ]
                },
                "social": {}
            }
        }
    ]
}

I will say though, that when i save changes to the tag people form, there is a tag list item that shows up in the person's data in the project json - i just can't seem to search through people and be able to add them. I just have issues rendering peoples names and ids into the form and peoples data in the background so that i can search through it and add them to the tag list



I might need to implement a function in my flask app that returns all people's data, this way i can search through it all for the tag people form

@app.route('/get_all_people')
def get_all_people():
    try:
        project_data = load_project_data()
        return jsonify(project_data.get('people', []))
    except Exception as e:
        print(f"Error in get_all_people: {str(e)}")
        return jsonify({'error': str(e)}), 500


One problem you might run into is that the create person form (add person) and edit person forms may overwrite tagged people data. 







I now want to add the functionality to create a network of people based on who they tag and render this on a new page "map.html". I want make a button on a user's profile next to "edit" and "delete" labeld "map". when clicked, this button will open a new tab with the url of the map page, load the data from the person's profile from which the map button was clicked, and then render a recursive, visual network of connections stemming from this individual. I want to use transitive relationship logic - if person1 is related to person2 and person2 is related to person3, then person3 is related to person1. I will consider the people tagged on a person's profile (the subject) as 1 hop from the subject, then the people tagged on the profiles of the people tagged on the subject's profile will be considered 2 hops from the subject. I want to keep track of the routes and combinations of hops between everybody, essentially performing recursion. I want to make a new page called "tagged.html" where I want to have a dynamic, visual graph of all the connections between all the people.

logic: if person1 is related to person2 and person2 is related to person3, then person3 is related to person1

feature: when person1 is tagged in person2's profile, update all other connections between people in the app recursively.



