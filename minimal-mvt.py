import http.server
import socketserver
import re
import psycopg2

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

HOST = 'localhost'
PORT = 8080


########################################################################

class TileRequestHandler(http.server.BaseHTTPRequestHandler):

    DATABASE_CONNECTION = None

    # Search REQUEST_PATH for /z/y/x.format patterns
    def pathToTile(self, path):
        m = re.search(r'^\/(\d+)\/(\d+)\/(\d+)\.(\w+)', path)
        if (m):
            return {'zoom':   int(m.group(1)), 
                    'x':      int(m.group(2)), 
                    'y':      int(m.group(3)), 
                    'format': m.group(4)}
        else:
            return None

    # Do we have all keys we need? 
    # Do the x/y coordinates make sense at this zoom level?
    def tileIsValid(self, tile):
        if 'x' not in tile or 'y' not in tile or 'zoom' not in tile or 'format' not in tile:
            return False
        if tile['format'] not in ['pbf', 'mvt']:
            return False
        size = 2 ** tile['zoom'];
        if tile['x'] >= size or tile['y'] >= size:
            return False
        return True

    # Calculate coordinates in spherical mercator (EPSG:3857)
    def tileToEnvelope(self, tile):
        # Width in EPSG:3857
        worldGeoMax = 20037508.3427892
        worldGeoMin = -1 * worldGeoMax
        worldGeoSize = worldGeoMax - worldGeoMin
        # Width in tiles
        worldTileSize = 2 ** tile['zoom']
        # Tile width in EPSG:3857
        tileGeoSize = worldGeoSize / worldTileSize
        tileX = tile['x']
        tileY = worldTileSize - tile['y']
        # Calculate geographic bounds from 
        env = dict()
        env['size'] = tileGeoSize
        env['xmin'] = worldGeoMin + tileGeoSize * tile['x']
        env['xmax'] = worldGeoMin + tileGeoSize * (tile['x'] + 1)
        env['ymin'] = worldGeoMax - tileGeoSize * (tile['y'] + 1)
        env['ymax'] = worldGeoMax - tileGeoSize * (tile['y'])
        return env


    def envelopeToBoundsSQL(self, env):
        # Densify edges of bounds so that when transformed to other coordinate
        # reference systems the edges partly respect curvature
        DENSIFY_FACTOR = 4
        env['segSize'] = (env['xmax'] - env['xmin'])/DENSIFY_FACTOR
        sql_tmpl = 'ST_Segmentize(ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax}, 3857),{segSize})'
        return sql_tmpl.format(**env)

        
    def envelopeToSQL(self, env):
        tbl = TABLE.copy()
        tbl['env'] = self.envelopeToBoundsSQL(env)
        # Materialize the bounds
        # Select the relevant geometry and clip to MVT bounds
        # Convert to MVT format
        sql_tmpl = """
            WITH 
            bounds AS (
                SELECT {env} AS geom, 
                       {env}::box2d AS b2d
            ),
            mvtgeom AS (
                SELECT ST_AsMVTGeom(ST_Transform(t.{geomColumn}, 3857), bounds.b2d) AS geom, 
                       {attrColumns}
                FROM {table} t, bounds
                WHERE ST_Intersects(t.{geomColumn}, ST_Transform(bounds.geom, {srid}))
            ) 
            SELECT ST_AsMVT(mvtgeom.*) FROM mvtgeom
        """
        return sql_tmpl.format(**tbl)


    def sqlToPbf(self, sql):
        # Make and hold connection to database
        if not self.DATABASE_CONNECTION:
            try:
                self.DATABASE_CONNECTION = psycopg2.connect(**DATABASE)
            except (Exception, psycopg2.Error) as error:
                self.send_error(500, "cannot connect: %s" % (str(DATABASE)))
                return None

        # Query for MVT
        with self.DATABASE_CONNECTION.cursor() as cur:
            cur.execute(sql)
            if not cur:
                self.send_error(404, "sql query failed: %s" % (sql))
                return None
            return cur.fetchone()[0]
        
        return None


    # Handle HTTP GET requests
    def do_GET(self):

        tile = self.pathToTile(self.path)
        if not (tile and self.tileIsValid(tile)):
            self.send_error(400, "invalid tile path: %s" % (self.path))
            return

        env = self.tileToEnvelope(tile)
        sql = self.envelopeToSQL(env)
        pbf = self.sqlToPbf(sql)

        self.log_message("path: %s\ntile: %s\n env: %s" % (self.path, tile, env))
        self.log_message("sql: %s" % (sql))

        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-type", "application/vnd.mapbox-vector-tile")
        self.end_headers()
        self.wfile.write(pbf)


########################################################################


with http.server.HTTPServer((HOST, PORT), TileRequestHandler) as server:
    try:
        print("serving at port", PORT)
        server.serve_forever()
    except KeyboardInterrupt:
        if self.DATABASE_CONNECTION:
            self.DATABASE_CONNECTION.close()
        print('^C received, shutting down server')
        server.socket.close()


