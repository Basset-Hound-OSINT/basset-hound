# basset-hound
Simplified Bloodhound but for OSINT 

## setup current working state - [commit 63dc3f5](https://github.com/gndpwnd/basset-hound/tree/63dc3f5ec37e3730d1a62c7031aff7a5d4474715)

> able to CRUD user data and render add/edit forms and profile based on data_config.yaml


Checkout the proper version of the code from the specific commit

```
git clone https://github.com/gndpwnd/basset-hound
cd basset-hound
git checkout 63dc3f5
```

Create the python environment
```
python3 -m venv venv
source venv/bin/activate
pip3 install flask pyaml
```

Run the app
```
python3 app.py
```

Visit the app in your web browser [here](http://localhost:5000)

```
http://localhost:5000
```


Observe how ***./projects*** is created when you make a project and how data is handled in ***./projects/{project_name}/***
- data is currently stored in JSON
	- got CRUD from data_config working
	- working on "tagging" functionality then will move to neo4j
- entities have their own folders
- all files are given a unique name
- just can't add a file where a file previously was