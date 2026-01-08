I have this repository and then the following external repositories that are meant to be independent projects but they're primarily built to extend to this existing project I just think everything all three repositories are large projects in of themselves that can stand alone and I simply want to make them integrate together but also be independent of each other.

~/autofill-extension
~/basset-hound-browser

and then the current local repository

~/basset-hound

Autofill extension auto search for data fields to allow users to click a button “ingest”

For information like crypto, email, phones, need to make sure data is plausible and ideally verify if exists. If not plausible then don’t allow ingest, but also want humans to be able to select html elements and auto copy content and take screenshots of pages.

For verify, need to find either algorithms or blockchain api for verifying wallet address, then need some probe or something or a Whois to see if domain exists and if email route exists for emails.


Basset hound keep track of where data comes from, either human operator entry or website, if website then have url and date

Autofill extension get full url and date for ingesting data


Somehow integrate into basset hound browser


OSINT agent use basset hound browser to perform automated investigations





Please take the ideas I just listed and do some sort of code review for every single repository and then add good updates or make sure these ideas are reflected in the road map.Md files for every single repository you may find the road map dot MD files and each repositories in the docs folder or something else but please do that comprehensive code review and figure out how I can integrate all these changes and make them all work together. Does this make sense? Feel free to spawn multiple agents as needed and let me know what you find you may need to also do web research so please document your findings into respective repositories where your research findings for various projects affect them differently. Effectively do research for all three repositories simultaneously but record your findings as they pertain to each project into the findings folder inside of the docs folder forever repository and then please also update every projects road map.Md to kind of help me understand how it would be implementing all these ideas or if there's better ideas please let me know. Feel free to call multiple agents as needed
Show less
I'll help you perform a comprehensive code review of all three repositories, research integration strategies, and update the roadmaps. Let me start by exploring all three codebases simultaneously.
Task:Explore basset-hound repository
IN
Thoroughly explore the ~/basset-hound repository. I need a comprehensive code review including:
1. Overall architecture and structure
2. Key features and functionality
3. Database schema and data models
4. API endpoints and interfaces
5. Current integration points or extensibility
6. Find and read the docs/ROADMAP.md or any roadmap file
7. Identify any existing docs folder structure
8. Technology stack used
9. Current state of completion
10. Any existing integration mechanisms
