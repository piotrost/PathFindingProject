# PathFindingProject
WUT PAG2 2024Z Education

A student implementation of graph algorithms for navigation based on Polish national BDOT10k road data.

# last stable version
'ToolboxScript_Improved_v3.py', 'PathFinding_Improved_v3.atbx'

# Additional console app
In 'console_test.py'.

# For Neo4j Spatial support:
1. watch this: https://www.youtube.com/watch?v=7uDXJld1aOg
2. replace plugin from the video with this: https://github.com/neo4j-contrib/spatial/releases/download/5.20.0/neo4j-spatial-5.20.0-server-plugin.jar
3. (if an error will show, open PROJECT settings(three dots near start/stop and open buttons) in Neo4j app (not Neo4j Browser) and replace line containing 'dbms.security.procedures.unrestricted' with 'dbms.security.procedures.unrestricted=*')
4. If the error from point 3. is another, unsolved error, contact PAGistczna Drużyna Cybergeodetów Help Team.

# snapping
MATCH (n:Node)
WITH n, point.distance(n.geom, point({x: 474133.3333, y: 474119.89, srid: 7203})) AS dist
ORDER BY dist ASC
LIMIT 1
RETURN n