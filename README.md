# basset-hound
Simplified Bloodhound but for OSINT 

## setup current working state - [commit 9aafa79](https://github.com/gndpwnd/basset-hound/tree/9aafa79e1f6d55193b4df4a0524a4596a5309fd9)

> able to CRUD user data and render add/edit forms and profile based on data_config.yaml


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