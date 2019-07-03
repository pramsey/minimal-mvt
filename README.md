# Python Setup

The tile server requires a database connection, so set up a virtual environment and then install the `psycopg2` driver using `pip`.

    cd minimal-mvt
    virtualenv --python python3 venv
    source venv/bin/activate
    pip install -r requirements.txt

# Configuration

Edit `minimal-mvt.py` and the `TABLE` and `DATABASE` constants:

    TABLE = {
        'table':'nyc_streets',
        'srid':'26918',
        'geomColumn':'geom',
        'attrColumns':'gid, name, type'
        }  

    DATABASE = {
        'user':'pramsey',
        'password':'password',
        'host':'localhost',
        'port':'5432',
        'database':'nyc'
        }

# Run 

    python3 minimal-mvt.py