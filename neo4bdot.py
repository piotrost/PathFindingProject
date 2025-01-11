import arcpy
import math
from neo4j import GraphDatabase

speed_dict = {'autostrada': 140, 'droga ekspresowa': 120, 'droga główna ruchu przyśpieszonego': 60, 'droga główna': 50,
              'droga zbiorcza': 40, 'droga lokalna': 30, 'droga dojazdowa': 30, 'droga wewnętrzna': 20}

# boundaries are whole 2180 epsg boundaries
create_node_geom_index = """CREATE POINT INDEX node_geom_index
FOR (n:Node) ON (n.geom)
OPTIONS {
  indexConfig: {
    `spatial.cartesian.min`: [144693.28, 125837.02],
    `spatial.cartesian.max`: [876500.36, 908411.19]
  }
}"""

# funkcja zaokrąglająca (rozwiązanie problemów z topologią)
def round_coords(coords):
    if coords is None:
        raise ValueError("No coordinates for rounding. check input data.")
    if isinstance(coords, arcpy.Point):
        coords = [coords.X, coords.Y]
    
    xy = (math.floor(coords[0]), math.ceil(coords[1]))
    xy1 = (math.ceil(coords[0]), math.floor(coords[1]))
    xy2 = (math.floor(coords[0]), math.floor(coords[1]))
    xy3 = (math.ceil(coords[0]), math.ceil(coords[1]))
    
    return xy, xy1, xy2, xy3

# utworzenie grafu w Neo4j
def generate_graph(file_path, driver):
    with driver.session(database="neo4j") as session:
        def tarnsaction_funct(tx):
            with arcpy.da.SearchCursor(file_path, ["FID", "SHAPE@", 'KLASA_DROG', 'DIRECTION']) as cursor:
                temp_nodes = {}                     # tymczasowy słownik ze zwielokrotnionymi kluczami
                for row in cursor:
                    edge_id = row[0]                # id krawędzi
                    shape = row[1]                  # geometria krawędzi
                    direction = row[3]              # kierunek krawędzi
                    first_point = shape.firstPoint  # pierwszy węzeł krawędzi
                    last_point = shape.lastPoint    # drugi węzeł krawędzi
                    length = shape.length           # długość krawędzi
                    speed = speed_dict[row[2]]      # prędkość krawędzi (na podstawie klasy drogi)
                    
                    xy_arr = []                                     # lista ostatecznych współrzędych węzłów krawędzi
                    for point in [first_point, last_point]:
                        coords = (point.X, point.Y)                 # współrzędne przed zaokrągleniem
                        xy, xy1, xy2, xy3 = round_coords(coords)    # wszystkie warianty zaoakrąglenia współrzędnych
                        
                        # nowy węzeł / pobranie współrzędnych istniejącego
                        for i, cr in enumerate([xy, xy1, xy2, xy3]):
                            if cr in temp_nodes:
                                xyf = temp_nodes[cr]                # współrzędne, dla których w poprzednich iteracjach już utworzono węzeł
                                break
                            elif i == 3:
                                # utworzenie nowego nietymczasowego węzła
                                tx.run("CREATE (:Node {geom: point({x: $x, y: $y, srid: $srid})})", x=xy[0], y=xy[1], srid=7203)  # srid=7203 - neo4j tak określa układ kartezjański bez wysokości
                                                                                                                                                           
                                xyf = xy                            # współrzędne utworzonego węzła
                        
                        # wszystkie klucze w słowniku tymczasowym wskazują na ten sam węzeł
                        temp_nodes[xy] = xyf
                        temp_nodes[xy1] = xyf
                        temp_nodes[xy2] = xyf
                        temp_nodes[xy3] = xyf
                        xy_arr.append(xyf)
                    
                    # czas przejazdu krawędzi
                    time = length / (speed * 1000 / 3600)
                    
                    # utworzenie krawędzi z uwzględnieniem kierunkowości dróg
                    if direction == "both" or direction == "ftl":
                        tx.run("MATCH (a:Node), (b:Node) WHERE a.geom.x = $x1 AND a.geom.y = $y1 AND b.geom.x = $x2 AND b.geom.y = $y2 CREATE (a)-[:Edge {edge_id: $edge_id, length: $length, time: $time}]->(b)",
                            x1=xy_arr[0][0], y1=xy_arr[0][1], x2=xy_arr[1][0], y2=xy_arr[1][1], edge_id=edge_id, length=length, time=time
                        )
                    if direction == "both" or direction == "ltf":
                        tx.run("MATCH (a:Node), (b:Node) WHERE a.geom.x = $x1 AND a.geom.y = $y1 AND b.geom.x = $x2 AND b.geom.y = $y2 CREATE (a)-[:Edge {edge_id: $edge_id, length: $length, time: $time}]->(b)",
                            x1=xy_arr[1][0], y1=xy_arr[1][1], x2=xy_arr[0][0], y2=xy_arr[0][1], edge_id=edge_id, length=length, time=time
                        )
        
        # wykonanie transakcji
        session.execute_write(tarnsaction_funct)
        print("Graph created successfully.")
        session.run(create_node_geom_index)
        print("Spatial index created successfully.")

if __name__ == "__main__":
    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "HelloThere")
    SHAPEFILE = r"data/nowy_SKJZ_L/torun/nowy_SKJZ_L_Torun_edited.shp"
    
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        try:
            driver.verify_connectivity()
        except Exception as e:
            print("Neo4j Connection error: ", e)
        
        generate_graph(SHAPEFILE, driver)     