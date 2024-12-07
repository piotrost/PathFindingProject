# Authors:  PAGistyczna Drużyna Cybergeodetów:
#           Remigiusz Szewczak
#           Maciej Mirowski
#           Piotr Ostaszewski
# Created:  2024-11-02T22:13:28.044Z

from heapdict import heapdict
import math
import pickle
import arcpy
import time

snap_call_counter = 0   # licznik dla poprawnego zapisu wielokrotnie wywoływanej funkcji snap
IDFIELD = None          # nazwa kolumny id w pliku źródłowym (kompatybilność gdb i shp)
a_map = None            # aktywna mapa
mess = ""               # zamiast print w ArcGisie

class Node:
    def __init__(self):  # współrzędne węzła są zapisane jako klucz w słowniku w klasie Graph
        self.edges = []  # lista krawędzi wychodzących z węzła
    
    def add_edge(self, x, y, edge_id, length, time):
        self.edges.append(Edge(x, y, edge_id, length, time))

class Edge:
    def __init__(self, x, y, edge_id, length, time):
        self.id = (x, y)        # współrzędne węzła do którego prowadzi krawędź
        self.edge_id = edge_id  # ID krawędzi z pliku źródłowego
        self.length = length
        self.time = time

# funkcje heurystyczne
def h_length(current, end):
    return math.sqrt((current[0] - end[0]) ** 2 + (current[1] - end[1]) ** 2)

def h_time(current, end):
    return math.sqrt((current[0] - end[0]) ** 2 + (current[1] - end[1]) ** 2) / 38.889  # (140 * 1000 / 3600) ~ 38.(8)

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

class Graph:
    def __init__(self, data_fc):
        self.data_fc = data_fc  # nazwa pliku źródłowego
        self.nodes = {}         # słownik węzłów
        self.generate_graph()   # utworzenie grafu
    
    def generate_graph(self):
        with arcpy.da.SearchCursor(self.data_fc, [IDFIELD, "SHAPE@", 'KLASA_DROG', 'DIRECTION']) as cursor:
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
                            self.nodes[xy] = Node()             # utworzenie nowego nietymczasowego węzła
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
                    self.nodes[xy_arr[0]].add_edge(xy_arr[1][0], xy_arr[1][1], edge_id, length, time)
                if direction == "both" or direction == "ltf":
                    self.nodes[xy_arr[1]].add_edge(xy_arr[0][0], xy_arr[0][1], edge_id, length, time)
        
        arcpy.management.AddSpatialIndex(self.data_fc)
    
    # eksport grafu do pliku tekstowego
    def export_graph_txt(self):
        with open("my_graph.txt", "w") as f:
            for node in self.nodes:
                f.write(f"\n\n\t<-- {node} -->\n")
                for edge in self.nodes[node].edges:
                    f.write(f"{edge.id}\t{edge.edge_id}\t{edge.length}\t{edge.time}\n")
    
    # implementacja algorytmu A*
    def aShift8(self, cost, h, start, end):
        # deklaracja struktur danych
        S = set()                                           # zbiór odwiedzonych węzłów
        S.add(start)
        Q = heapdict()                                      # kolejka priorytetowa sąsiadów odwiedzonych węzłów
        p = {start: (None, None)}                           # słownik poprzedników
        
        # sąsiedzi pierwszego węzła
        for edge in self.nodes[start].edges:
            future_h = h(edge.id, end)                                                  # h dla węzła na końcu krawędzi, raz obliczone nie zmienia się
            Q[edge.id] = getattr(edge, cost) + future_h, getattr(edge, cost), future_h  # dodanie f, g, h dla węzła na końcu krawędzi
            p[edge.id] = start, edge.edge_id                                            # dodanie poprzednika i id prowadzącej do niego krawędzi
        
        # główna pętla
        while Q:                                            # wyjście z pętli w razie nieznalezienia ścieżki
            curr, (curr_f, curr_g, curr_h) = Q.popitem()    # f, g, h dla bieżącego węzła
            
            # wyniki końcowe po dotarciu do celu
            if curr == end:
                node_path = [end]
                edge_ids = []
                curr = (end, None)                          # zmiana do iteracji w poniższej pętli
                
                while curr[0] != start:
                    curr = p[curr[0]]                       # zmiana zmiennej curr
                    node_path.append(curr[0])               # dodanie węzła
                    edge_ids.append(curr[1])                # dodanie krawędzi
                
                # powrót do dobrej kolejności
                node_path.reverse()
                edge_ids.reverse()
                
                return node_path, edge_ids, curr_g, len(S)  # węzły ścieżki, krawędzie ścieżki, koszt, ilość węzłów w S
            
            # dodanie węzła do zbioru S
            S.add(curr)
            for edge in self.nodes[curr].edges:
                if edge.id not in S:
                    if edge.id not in Q:
                        future_h = h(edge.id, end)                                      # h dla węzła na końcu krawędzi, raz obliczone nie zmienia się
                        future_g = curr_g + getattr(edge, cost)                         # g dla węzła na końcu krawędzi
                        Q[edge.id] = future_g + future_h, future_g, future_h            # dodanie f, g, h dla węzła na końcu krawędzi
                        p[edge.id] = curr, edge.edge_id
                    else:
                        new_old_h = Q[edge.id][2]                                       # odczyt oblilczonego wcześniej h
                        new_g = curr_g + getattr(edge, cost)                            # nowa wartość g
                        new_f = new_g + new_old_h                                       # nowa wartość f
                        
                        # relaksacja krawędzi
                        if new_f < Q[edge.id][0]:                                       # Q[edge.xy][0] = stara wartość f
                            Q[edge.id] = new_f, new_g, new_old_h                        # f, g, h
                            p[edge.id] = curr, edge.edge_id                             # dodanie do tablicy poprzedników
    
    # wyznaczanie zasięgu na podstawie algorytmu Dijkstry
    def dijkstra_with_time_limit(self, start, max_time):
        visited = set()                                     # odwiedzone węzły
        times = {start: 0}                                  # odległości od startu
        queue = heapdict()                                  # kolejka priorytetowa dla algorytmu Dijkstry
        queue[start] = 0
        reachable_nodes = []                                # lista osiągalnych węzłów
        
        while queue:
            # Pobieranie węzła o najmniejszym koszcie z kolejki
            current_node, current_time = queue.popitem()
            # Sprawdzanie, czy węzeł przekracza maksymalny dystans
            if current_time > max_time:
                continue  # Pomijanie węzłów, które przekraczają maksymalny dystans
            
            # Dodawanie węzła do odwiedzonych
            visited.add(current_node)
            reachable_nodes.append(current_node)
            
            # Iteracja po sąsiadach bieżącego węzła
            for edge in self.nodes[current_node].edges:
                neighbor = edge.id
                new_time = current_time + edge.time
                # Jeśli węzeł został odwiedzony lub nowa odległość przekracza maksymalny dystans, pomijamy
                if neighbor in visited or new_time > max_time:
                    continue
                # Jeśli nowa odległość jest lepsza, aktualizujemy i dodajemy do kolejki
                if neighbor not in times or new_time < times[neighbor]:
                    times[neighbor] = new_time
                    queue[neighbor] = new_time
        
        return reachable_nodes
    
    # eksport wybranych dróg do nowej warstwy i klasy
    def export_fc(self, ids, name):
        filter = f"{IDFIELD} IN ({', '.join(str(id) for id in ids)})"
        edges = arcpy.management.SelectLayerByAttribute(self.data_fc, "NEW_SELECTION", filter)
        arcpy.management.CopyFeatures(edges, name)
        add_fc_to_map(name)
        arc_prnt(f"Created feature class '{name}'.")
    
    # eksport wyników Dijkstry jako otoczka wklęsła
    def export_dijkstra_as_concave_hull(self, reachable_nodes, name, alpha=40000.0):
        from shapely.geometry import MultiPoint, Polygon
        from shapely.ops import triangulate, unary_union
        
        # utworzenie otoczki wklęsłej
        multi_point = MultiPoint(reachable_nodes)
        triangles = triangulate(multi_point)
        arc_prnt(f"Count of triangles: {len(triangles)}")
        
        # filtrowanie: 'alpha'= obszar trójkąta
        concave_hull = unary_union([tri for tri in triangles if tri.area < alpha])
        
        # różne typy geometrii
        polygons = []
        if concave_hull.geom_type == "Polygon":
            polygons = [concave_hull]
        elif concave_hull.geom_type == "MultiPolygon":
            polygons = list(concave_hull.geoms)
        elif concave_hull.geom_type == "GeometryCollection":
            polygons = [geom for geom in concave_hull.geoms if isinstance(geom, Polygon)]
        
        arc_prnt(f"concave hull geometry: {concave_hull.geom_type}")
        if not polygons:
            arc_prnt("No polygons to write in concave hull.")
            return
        
        # utworzenie warstwy z otoczką wklęsłą
        arcpy.management.CreateFeatureclass(
            arcpy.env.workspace, name, geometry_type="POLYGON",spatial_reference=arcpy.env.outputCoordinateSystem
        )
        with arcpy.da.InsertCursor(name, ["SHAPE@"]) as cursor:
            for poly in polygons:
                arc_polygon = arcpy.Polygon(
                    arcpy.Array([arcpy.Point(*coords) for coords in poly.exterior.coords])
                )
                cursor.insertRow([arc_polygon])
        
        # dodanie warstwy do mapy
        add_fc_to_map(name)
        arc_prnt(f"Created feature class '{name}' as a concave hull.")
    
    # funkcja dociągająca punkty do grafu
    def snap(self, start, end):     
        global snap_call_counter
        snap_call_counter += 1                                              # licznik wywołań funkcji snap
        input_points_name = f"PF_input_points_{snap_call_counter}"
        snap_to_graph_name = f"PF_snap_to_graph_{snap_call_counter}"
        
        # posprzątanie po snapowaniu w poprzednim wywołaniu skryptu
        try:
            arcpy.Delete_management(snap_to_graph_name)
            remove_layer_from_map(snap_to_graph_name)
        except:
            pass

        # utworzenie klasy punktów wejściowych
        arcpy.management.CreateFeatureclass(arcpy.env.workspace, input_points_name, 'POINT')
        with arcpy.da.InsertCursor(input_points_name, ["SHAPE@"]) as insert_cursor:
            for point in [start, end]:
                insert_cursor.insertRow([arcpy.Point(point[0], point[1])])
        
        outside_graph = []                                                  # punkty spoza grafu
        start_end_final = [None, None]                                      # ostateczne punkty startu i końca                    
        
        # sprawdzenie, czy punkty są w grafie
        for i, point in enumerate([start, end]):
            xy, xy1, xy2, xy3 = round_coords(point)
            for j, cr in enumerate([xy, xy1, xy2, xy3]):
                if cr in self.nodes:
                    start_end_final[i] = cr
                    break
                elif j == 3:
                    outside_graph.append(point)
        
        # czas i długość dotarcia do grafu
        time = 0
        length = 0
        
        if len(outside_graph) == 0:                                         # oba punkty są w grafie
            add_fc_to_map(input_points_name)
            return start_end_final, length, time
        else:            
            # znalezienie najbliższych krawędzi
            arcpy.analysis.Near(input_points_name, self.data_fc, 500, "LOCATION")
            
            # pobranie id najbliższych krawędzi i geometrii punktów do dosnapowania
            near_line_ids = []
            out_point_shapes = [] 
            with arcpy.da.SearchCursor(input_points_name, ["NEAR_FID", "SHAPE@"]) as cursor:
                for row in cursor:
                    near_line_ids.append(row[0])
                    out_point_shapes.append(row[1])
            
            # pobranie geometrii krawędzi
            edge_shapes_dict = {}
            edge_shapes = []
            filter = f"{IDFIELD} IN ({', '.join(map(str, near_line_ids))})"
            with arcpy.da.SearchCursor(self.data_fc, [IDFIELD, "SHAPE@"], filter) as edge_cursor:
                for edge_row in edge_cursor:
                    edge_shapes_dict[edge_row[0]] = edge_row[1]
            
            # posortowanie krawędzi
            for i, fid in enumerate(near_line_ids):
                edge_shapes.append(edge_shapes_dict[fid])
            
            # wybór bliższego wierzchołka krawędzi, do której przyłączane są punkty
            with arcpy.da.UpdateCursor(input_points_name, ["NEAR_X", "NEAR_Y"]) as update_cursor:
                k = 0
                for row in update_cursor:
                    out_point_shape = out_point_shapes[k]
                    edge_shape = edge_shapes[k]
                    first_point = edge_shape.firstPoint
                    last_point = edge_shape.lastPoint
                    if out_point_shape.distanceTo(first_point) < out_point_shape.distanceTo(last_point):
                        update_cursor.updateRow([first_point.X, first_point.Y])
                    else:
                        update_cursor.updateRow([last_point.X, last_point.Y])
                    k += 1
            
            # utworzenie klasy odcinów łączących punkty z grafem
            arcpy.management.CreateFeatureclass(arcpy.env.workspace, snap_to_graph_name, 'POLYLINE')
            field_names = ["F_POINT", "L_POINT"]
            field_types = ["TEXT", "TEXT"]
            for field_name, field_type in zip(field_names, field_types):
                arcpy.AddField_management(snap_to_graph_name, field_name, field_type)
            
            # dodanie lini łączących punkty z grafem
            with arcpy.da.SearchCursor(input_points_name, ["SHAPE", "NEAR_X", "NEAR_Y"]) as cursor:
                with arcpy.da.InsertCursor(snap_to_graph_name, ["F_POINT", "L_POINT", "SHAPE@"]) as insert_cursor:
                    for i, row in enumerate(cursor):
                        out_point_shape = row[0]
                        near_x = row[1]
                        near_y = row[2]
                        line = arcpy.Polyline(arcpy.Array(
                            [arcpy.Point(out_point_shape[0], out_point_shape[1]), arcpy.Point(near_x, near_y)]))
                        insert_cursor.insertRow(
                            ["(" + str(out_point_shape[0]) + "," + str(out_point_shape[1]) + ")", str(cr), line])
                        
                        # koszt i czas dotarcia do grafu
                        length += line.length
                        time += line.length / (speed_dict['droga wewnętrzna'] * 1000 / 3600)
                        
                        # aktualizacja punktów startu i końca na podstawie słownika klasy Graph
                        xy, xy1, xy2, xy3 = round_coords((near_x, near_y))
                        for cr in [xy, xy1, xy2, xy3]:
                            if cr in self.nodes:
                                if len(outside_graph) == 2:
                                    start_end_final[i] = cr
                                else:
                                    for j, item in enumerate(start_end_final):
                                        if item == None:
                                            start_end_final[j] = cr
                                break
                
                # dodanie warstw do mapy
                add_fc_to_map(snap_to_graph_name)
                add_fc_to_map(input_points_name)
                
                return start_end_final, length, time    # punkty, długość odcinków snapujących, czas pokonania odcinków snapujących

# funkcja generująca graf bez wykonywania algorytmów nawigacyjnych
def generate_launcher(in_data_fc, out_graph_file="PF_graph.pkl"):
    # utworzenie grafu
    g = Graph(in_data_fc)
    
    # zapis przy pomocy biblioteki pickle
    with open(out_graph_file, 'wb') as f:
        pickle.dump(g, f)

# funkcja wywołująca algorytm A*
def aS8_launcher(out_mode, start, end, output_name="PF", in_data_fc=None, in_graph_file="PF_graph.pkl", create_new_graph=False):
    # tworzenie nowego grafu
    if create_new_graph:
        g = Graph(in_data_fc)
    else:
        # odczyt grafu z pliku pickle
        with open(in_graph_file, 'rb') as f:
            g: Graph = pickle.load(f)
        
        # zmiana nazwy pliku źródłowego (może być przydatna w przypadku pracy z plikiem pickle)
        if in_data_fc:
            g.data_fc = in_data_fc
    
    # najkrótsza lub najszybsza ścieżka
    if out_mode == "Both":
        mode_arr = ["Shortest_Path", "Fastest_Path"]
    else:
        mode_arr = [out_mode]
    
    # wywołanie funkcji snapującej
    start_end_list, snap_length, snap_time = g.snap(start, end)
    start = start_end_list[0]
    end = start_end_list[1]
    
    # algorytm A*
    for mode in mode_arr:
        # parametry dla aktualnego trybu
        if mode == "Shortest_Path":
            cost_field = "length"
            h_funct = h_length
        elif mode == "Fastest_Path":
            cost_field = "time"
            h_funct = h_time
        
        # A*
        t_alg_0 = time.time()
        path, edge_ids, cost, vol_S = g.aShift8(cost_field, h_funct, start, end)
        t_alg_1 = time.time()
        arc_prnt(f"Time of {mode} A* algorithm: {t_alg_1 - t_alg_0} s")
        
        # wydruk wyników
        if mode == "Shortest Path":
            arc_prnt("length of the road:    " + str(cost / 1000) + "km")
            if snap_length != 0:
                arc_prnt("length of the snap:    " + str(snap_length) + "m")
        elif mode == "Fastest Path":
            arc_prnt("time of the road:    "+ str(cost / 60) + " min")
            if snap_time != 0:
                arc_prnt("time of the snap:    " + str(snap_time) + " s")
        
        arc_prnt("volume of S:    " + str(vol_S))
        arc_prnt('path vertices count: '+ str(len(path)))
        arc_prnt('path edges count:   ' +  str(len(edge_ids)))

        # wyjściowa klasa
        g.export_fc(edge_ids, output_name + "_" + mode)
        arc_prnt("\n")

# funkcja wywołująca algorytm wyznaczania zasięgu
def Dijsktra_launcher(start,time_max, in_data_fc=None,output_name="PF", in_graph_file="PF_graph.pkl", create_new_graph=False):
    if create_new_graph:
        g = Graph(in_data_fc)
    else:
        # odczyt grafu z pickle
        with open(in_graph_file, 'rb') as f:
            g: Graph = pickle.load(f)
        # opcjonalna zmiana nazwy pliku źródłowego
        if in_data_fc:
            g.data_fc = in_data_fc
    
    # snapowanie punktu początkowego
    start_end_list, snap_length, snap_time = g.snap(start, start)
    start = start_end_list[0]
    
    # osiągnięte węzły
    algorithm_start = time.time()
    reachable_nodes = g.dijkstra_with_time_limit(start, time_max)
    algorithm_end = time.time()
    arc_prnt(f"Nodes reached in time {time_max} s count: {len(reachable_nodes)}")
    arc_prnt(f"Time of Dijkstra reach algorithm: {algorithm_end - algorithm_start} s")
    

    # Eksport wyników Dijkstry
    dijkstra_edges = []
    for node in reachable_nodes:
        for edge in g.nodes[node].edges:
            if edge.id in reachable_nodes and edge.id not in dijkstra_edges:
                dijkstra_edges.append(edge.edge_id)
        reachable_coords = []
        for node in reachable_nodes:
            for rounded_coord in round_coords(node):
                if rounded_coord in g.nodes:
                    reachable_coords.append(rounded_coord)
                    break
    
    # Eksportowanie wyników
    g.export_fc(dijkstra_edges, output_name + "_range_of_reach_edges")
    g.export_dijkstra_as_concave_hull(reachable_coords, output_name + "_range_of_reach_polygon")
            
        
speed_dict = {'autostrada': 140, 'droga ekspresowa': 120, 'droga główna ruchu przyśpieszonego': 60, 'droga główna': 50,
              'droga zbiorcza': 40, 'droga lokalna': 30, 'droga dojazdowa': 30, 'droga wewnętrzna': 20}

# dodanie warstwy do mapy - tylko dla GUI Script tool
def add_fc_to_map(fc_name):
    global a_map
    if a_map is not None:
        a_map.addDataFromPath(arcpy.env.workspace + "\\" + fc_name)

# usunięcie warstwy z mapy - tylko dla GUI Script tool
def remove_layer_from_map(layer_name):
    global a_map
    if a_map is not None:
        all = a_map.listLayers()
        for layer in all:
            if layer.name == layer_name:
                a_map.removeLayer(layer)

# Script tool nie słucha się funkckji print
def arc_prnt(message):
    global mess
    print(message)
    if a_map is not None:
        mess += message + "\n"

if __name__ == '__main__':
    # aktywna mapa
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    a_map = aprx.activeMap
    
    # ustawienia geobazy
    arcpy.env.workspace = aprx.defaultGeodatabase
    arcpy.env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference('ETRF2000-PL CS92')
    
    # PARAMETRY
    # źródło danych
    input_file = arcpy.GetParameterAsText(0)
    if ".shp" in input_file:
        IDFIELD = "FID"                             # shp
    else:
        IDFIELD = "OBJECTID"                        # gdb
    
    mode = arcpy.GetParameterAsText(1)              # [Both, Fastest_Path, Shortest_Path]
    startpoint = arcpy.GetParameter(2)              # Feature Set, punkt początkowy wyznaczania trasy
    endpoint = arcpy.GetParameter(3)                # Feature Set, punkt końcowy wyznaczania trasy
    Range_of_Reach=arcpy.GetParameterAsText(4)      # [true, false]
    
    try:
        max_time = int(arcpy.GetParameterAsText(5)) # czas dojazdu do wyznaczania zasięgu [s]
    except:
        pass
    
    try:
        point_of_intrest = arcpy.GetParameter(6)    # Feature Set, punkt początkowy wyznaczania zasięgu
    except:
        pass
    
    # pobranie geometrii punktu startowego wyznaczania trasy
    try:
        start_coords = None
        with arcpy.da.SearchCursor(startpoint, ['SHAPE@']) as cursor:
            for row in cursor:
                start_coords = row[0]  # Współrzędne "Startpoint"
        
        if start_coords:
            start = [start_coords.firstPoint.X, start_coords.firstPoint.Y]
        else:
            raise ValueError("Could not succesfully get Startpoint coordinates.")
    except Exception as e:
        arc_prnt(f"Error while setting start point coordinates: {e}")
        start = None
    
    # pobranie geometrii punktu końcowego wyznaczania trasy
    try:
        end_coords = None
        with arcpy.da.SearchCursor(endpoint, ['SHAPE@']) as cursor:
            for row in cursor:
                end_coords = row[0]  # Współrzędne "Endpoint"
        
        if end_coords:
            end = [end_coords.firstPoint.X, end_coords.firstPoint.Y]
        else:
            raise ValueError("Could not succesfully get Endpoint coordinates.")
    except Exception as e:
        arc_prnt(f"Error while setting end point coordinates: {e}")
        end = None
    
    # pobranie geometrii punktu zainteresowania
    if Range_of_Reach=="true":
        try:
            Point_of_Intrest = None
            with arcpy.da.SearchCursor(point_of_intrest, ['SHAPE@']) as cursor:
                for row in cursor:
                    Point_of_Intrest = row[0]  # Współrzędne "Point_of_Intrest"
            
            if Point_of_Intrest:
                PoI = [Point_of_Intrest.firstPoint.X, Point_of_Intrest.firstPoint.Y]
            else:
                arc_prnt("No Point of Interest given.")
                PoI = None
        except Exception as e:
            arc_prnt(f"Error while setting Point of Interest coordinates: {e}")
            PoI = None
    
    # ALGORYTMY
    # A*
    t0 = time.time()
    aS8_launcher(
        out_mode=mode,
        start=start,
        end=end,
        output_name="PF",
        in_data_fc=input_file,
        create_new_graph=True
    )
    t1 = time.time()
    arc_prnt("time A* and visualization: "+ str(t1 - t0) + "s\n")
    
    # Zasięg
    if Range_of_Reach=="true":
        t0 = time.time()
        Dijsktra_launcher(
            start=PoI,
            time_max=max_time,
            output_name="PF",
            in_data_fc=input_file,
            create_new_graph=True            
        )
        t1 = time.time()
        arc_prnt("time of generating range of reach and visualization: "+str(t1 - t0) + "s\n")

    # wyświetlenie komunikatów w ArcGIS Pro GUI
    if a_map is not None:
        arcpy.AddMessage(mess)

    # sprzątanie automatycznie wygenerowanych klas
    try:
        arcpy.Delete_management("Points_2")
    except:
        pass
    
    try:
        arcpy.Delete_management("Points_2_1")
    except:
        pass        
    
    try:
        arcpy.Delete_management("Points_2_2")
    except:
        pass
    
    # sprzątanie automatycznie wygenerowanych warstw
    try:
        if startpoint.name == "PathFinding Startpoint (Points)": 
            remove_layer_from_map(startpoint.name)
    except:
        pass
    try:
        if endpoint.name == "PathFinding Endpoint (Points)": 
            remove_layer_from_map(endpoint.name)
    except:
        pass
    try:
        if point_of_intrest.name == "PathFinding Point of Intrest (Points)":
            remove_layer_from_map(point_of_intrest.name)
    except:
        pass