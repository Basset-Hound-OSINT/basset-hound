# basset-hound
Simplified Bloodhound but for OSINT 

## setup old version with JSON storage - [commit 63dc3f5](https://github.com/gndpwnd/basset-hound/tree/63dc3f5ec37e3730d1a62c7031aff7a5d4474715)

> able to CRUD user data and render add/edit forms and profile based on data_config.yaml

Running just Neo4j

```bash
docker compose up -d neo4j
docker compose down -v

# more agressive cleanup of non used containers not defined in the compose file
docker compose down --volumes --remove-orphans
```


Checkout the proper version of the code from the specific commit

```
git clone https://github.com/gndpwnd/basset-hound
cd basset-hound
git checkout 9aafa79
```

Create the python environment
```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
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
Other than that - feel free to find bugs and report