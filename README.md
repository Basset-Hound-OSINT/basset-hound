<td width="100" align="center">

<img src="static/imgs/basset_hound_osint_logo.png">

</td>

# basset-hound
A BloodhoundAD-inspired tool for OSINT 

**Running just Neo4j**

```bash
docker compose up -d neo4j
docker compose down -v

# more agressive cleanup of non used containers not defined in the compose file
docker compose down --volumes --remove-orphans
```

**Run setup the python environment**

```
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Run the app**

```bash
python3 app.py
```

Visit the app in your web browser [here](http://localhost:5000)

```
http://localhost:5000
```