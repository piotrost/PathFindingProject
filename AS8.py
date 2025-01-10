# Authors: PAGistyczna Drużyna Cybergeodetów
# Created:  2024-11-02T22:13:28.044Z

from heapdict import heapdict
import math
import pickle
import arcpy

class Node:
    def __init__(self):                             # no need to store node's coordinates - they are keys in "nodes" dictionary
        self.edges = []                             # keys to nodes in the "nodes dictionary" + edge info

    def add_edge(self, x, y, edge_id, length, time):
        self.edges.append(Edge(x, y, edge_id, length, time))

class Edge:
    def __init__(self, x, y, edge_id, length, time):
        self.id = (x, y)
        self.edge_id = edge_id                      # for visualization 
        self.length = length                             
        self.time = time
    
# h functions
def h_length(current, end):                                    
    return math.sqrt((current[0] - end[0])**2 + (current[1] - end[1])**2)

def h_time(current, end):
    return math.sqrt((current[0] - end[0])**2 + (current[1] - end[1])**2) / 38.889  # / (140 * 1000 / 3600) ~ 38.(8)

# rounding function (all possibilities)
def round_coords(coords):
    xy = (math.floor(coords[0]), math.ceil(coords[1]))
    xy1 = (math.ceil(coords[0]), math.floor(coords[1]))
    xy2 = (math.floor(coords[0]), math.floor(coords[1]))
    xy3 = (math.ceil(coords[0]), math.ceil(coords[1]))

    return xy, xy1, xy2, xy3

class Graph:
    def __init__(self, data_fc, driver=None):
        self.data_fc = data_fc                        # graph source line fc name
        self.nodes = {}                               # the nodes - core data structure for A*
        self.generate_graph(driver)
    
    def generate_graph(self, driver):
        with driver.session(database="neo4j") as session:
            def tarnsaction_funct(tx):
                # create graph
                with arcpy.da.SearchCursor(arcpy.env.workspace + "\\" + self.data_fc, ["OBJECTID", "SHAPE@", 'KLASA_DROG', 'DIRECTION']) as cursor:
                    temp_nodes = {}                         # store the nodes' final rounded coordinates under multiple keys
                    
                    for row in cursor:
                        edge_id = row[0]                    # edge OBJECTID   
                        shape = row[1]                      # edge geometry
                        direction = row[3]                  # edge direction

                        first_point = shape.firstPoint      # node
                        last_point = shape.lastPoint        # second node
                        length = shape.length               # edge length
                        speed = speed_dict[row[2]]          # route speed

                        xy_arr = []                         # final nodes' coordinates
                        
                        for point in [first_point, last_point]:
                            coords = (point.X, point.Y)                 # raw coords
                            xy, xy1, xy2, xy3 = round_coords(coords)    # rounded coords

                            for i, cr in enumerate([xy, xy1, xy2, xy3]):
                                if cr in temp_nodes:
                                    xyf = temp_nodes[cr]
                                elif i == 3:
                                    self.nodes[xy] = Node()             # create a new node
                                    tx.run("CREATE (:Node {x: $x, y: $y})", x=xy[0], y=xy[1])
                                    xyf = xy                            # set final rounded coordinates
                            
                            # all possible coordinate keys leed to the same rounded one
                            temp_nodes[xy] = xyf; temp_nodes[xy1] = xyf; temp_nodes[xy2] = xyf; temp_nodes[xy3] = xyf
                            xy_arr.append(xyf)
                        
                        # edge time
                        time = length / (speed * 1000/3600)

                        # create edges - based on direction attribute
                        if direction == "both" or direction == "ftl":
                            self.nodes[xy_arr[0]].add_edge(xy_arr[1][0], xy_arr[1][1], edge_id, length, time)
                            tx.run("MATCH (a:Node), (b:Node) WHERE a.x = $x1 AND a.y = $y1 AND b.x = $x2 AND b.y = $y2 CREATE (a)-[:Edge {edge_id: $edge_id, length: $length, time: $time}]->(b)", x1=xy_arr[0][0], y1=xy_arr[0][1], x2=xy_arr[1][0], y2=xy_arr[1][1], edge_id=edge_id, length=length, time=time)
                        if direction == "both" or direction == "ltf":
                            self.nodes[xy_arr[1]].add_edge(xy_arr[0][0], xy_arr[0][1], edge_id, length, time)
                            tx.run("MATCH (a:Node), (b:Node) WHERE a.x = $x1 AND a.y = $y1 AND b.x = $x2 AND b.y = $y2 CREATE (a)-[:Edge {edge_id: $edge_id, length: $length, time: $time}]->(b)", x1=xy_arr[1][0], y1=xy_arr[1][1], x2=xy_arr[0][0], y2=xy_arr[0][1], edge_id=edge_id, length=length, time=time)
                arcpy.management.AddSpatialIndex(self.data_fc)
            
            session.execute_write(tarnsaction_funct)

    def export_graph_txt(self):
        with open("my_graph.txt", "w") as f:
            for node in self.nodes:
                f.write(f"\n\n\t<-- {node} -->\n")
                for edge in self.nodes[node].edges:
                    f.write(f"{edge.id}\t{edge.edge_id}\t{edge.length}\t{edge.time}\n")

    def aShift8(self, cost, h, start, end):
        # create data structures
        S = set(); S.add(start)
        Q = heapdict()
        p = {start: (None, None)}                      

        # first node's neighbours
        for edge in self.nodes[start].edges:
            future_h = h(edge.id, end)                                                  # h for new node - it will never be changed
            Q[edge.id] = getattr(edge, cost) + future_h, getattr(edge, cost), future_h  # f, g, h for nodes added to Q - possible FUTURE S elements
            p[edge.id] = start, edge.edge_id
        
        # main algorithm loop
        while Q:                                                        # ensure loop exit when no solution
            curr, (curr_f, curr_g, curr_h) = Q.popitem()                # f, g, h of CURRENT node
            
            # destination reached
            if curr == end:
                node_path = [end]; edge_ids = []                        # create output data structures
                curr = (end, None)                                      # adjust curr for loop
                while curr[0] != start:
                    curr = p[curr[0]]                                   # alter curr
                    node_path.append(curr[0])                           # append node
                    edge_ids.append(curr[1])                            # append edge
                
                node_path.reverse(); edge_ids.reverse()
                return node_path, edge_ids, curr_g, len(S)
            
            # add the current node to the S set
            S.add(curr)

            for edge in self.nodes[curr].edges:
                if edge.id not in S:
                    if edge.id not in Q:
                        future_h = h(edge.id, end)                              # h for new node - it will never be changed
                        future_g = curr_g + getattr(edge, cost)                 # g for new node                      
                        Q[edge.id] = future_g + future_h, future_g, future_h    # f, g, h
                        p[edge.id] = curr, edge.edge_id
                    else:
                        new_old_h = Q[edge.id][2]                               # read Q[edge.xy][2] = old_but_up_to_date_h
                        new_g = curr_g + getattr(edge, cost)                    # count possibly_different_value_of_g
                        new_f = new_g + new_old_h                               # count new f based on f and g above
                        # relax the edge (if needed)
                        if new_f < Q[edge.id][0]:                               # Q[edge.xy][0] = old_f
                            Q[edge.id] = new_f, new_g, new_old_h                # f, g, h
                            p[edge.id] = curr, edge.edge_id

    def export_fc(self, oids, name):           
            filter = f"OBJECTID IN ({', '.join(str(oid) for oid in oids)})"
            edges = arcpy.management.SelectLayerByAttribute(self.data_fc, "NEW_SELECTION", filter)
            arcpy.management.CopyFeatures(edges, name)

            print(f"Created feature class '{name}'.")
    
    def snap(self, start, end):
        # delete previous snap feature classes
        try:
            arcpy.Delete_management("reach_graph")
        except:
            pass
        try:
            arcpy.Delete_management("ends_outside_graph")
        except:
            pass
        
        outside_graph = []; start_end_final = [None, None]
        # check for prescence in the graph
        for j, point in enumerate([start, end]):
            xy, xy1, xy2, xy3 = round_coords(point)
            for j, cr in enumerate([xy, xy1, xy2, xy3]):
                if cr in self.nodes:
                    start_end_final[j] = cr; break
                elif j == 3:
                    outside_graph.append(point)
        
        # time and length of snap lines
        time = 0; length = 0 
        
        if len(outside_graph) == 0:
            # both points are in the graph
            return [start, end], length, time
        else:        
            # create unsnapped_points fc
            arcpy.management.CreateFeatureclass(arcpy.env.workspace, "ends_outside_graph", 'POINT')
            with arcpy.da.InsertCursor("ends_outside_graph", ["SHAPE@"]) as insert_cursor:
                for point in outside_graph:
                    insert_cursor.insertRow([arcpy.Point(point[0], point[1])])
            
            # find the nearest edges
            arcpy.analysis.Near("ends_outside_graph", self.data_fc, 500, "LOCATION")

            # get the nearest edges' OBJECTIDs and outside graph points' shapes
            near_line_fids = []; out_point_shapes = []
            with arcpy.da.SearchCursor("ends_outside_graph", ["NEAR_FID", "SHAPE@"]) as cursor:
                for row in cursor:
                    near_line_fids.append(row[0])
                    out_point_shapes.append(row[1])

            # get the nearest edges' shapes
            edge_shapes_dict = {}; edge_shapes = []                        
            filter = f"OBJECTID IN (SELECT NEAR_FID FROM ends_outside_graph)"
            with arcpy.da.SearchCursor(self.data_fc, ["OBJECTID", "SHAPE@"], filter) as edge_cursor:
                for edge_row in edge_cursor:
                    edge_shapes_dict[edge_row[0]] = edge_row[1]
            
            # sort the edge shapes
            for i, fid in enumerate(near_line_fids):
                edge_shapes.append(edge_shapes_dict[fid])

            # update the NEAR_X and NEAR_Y in outside graph points
            with arcpy.da.UpdateCursor("ends_outside_graph", ["NEAR_X", "NEAR_Y"]) as update_cursor:
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
                    

            # create output reach_graph feature class in gdb
            arcpy.management.CreateFeatureclass(arcpy.env.workspace, "reach_graph", 'POLYLINE')
            
            field_names = ["F_POINT", "L_POINT"]
            field_types = ["TEXT", "TEXT"]

            for field_name, field_type in zip(field_names, field_types):
                arcpy.AddField_management("reach_graph", field_name, field_type)

            # insert output into reach_graph
            with arcpy.da.SearchCursor("ends_outside_graph", ["SHAPE", "NEAR_X", "NEAR_Y"]) as cursor:
                with arcpy.da.InsertCursor("reach_graph", ["F_POINT", "L_POINT", "SHAPE@"]) as insert_cursor:
                    for i, row in enumerate(cursor):
                        out_point_shape = row[0]
                        near_x = row[1]; near_y = row[2]
                        
                        line = arcpy.Polyline(arcpy.Array([arcpy.Point(out_point_shape[0], out_point_shape[1]), arcpy.Point(near_x, near_y)]))
                        insert_cursor.insertRow(["(" + str(out_point_shape[0]) + "," + str(out_point_shape[1]) + ")" , str(cr), line])
                        length += line.length
                        time += line.length / (speed_dict['droga wewnętrzna'] * 1000/3600)

                        # start and end last possible modification
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

                return start_end_final, length, time

def generate_launcher(in_data_fc, out_graph_file="graph.pkl"):
    # create graph
    g = Graph(in_data_fc)

    # save graph with pickle
    with open(out_graph_file, 'wb') as f:
        pickle.dump(g, f)

def aS8_launcher(out_mode, start, end, output_name = "output", in_data_fc=None, in_graph_file="graph.pkl", create_new_graph=False, driver=None):
    if create_new_graph:
        g = Graph(in_data_fc, driver)
    else:
        # read graph with pickle
        with open(in_graph_file, 'rb') as f:
            g: Graph = pickle.load(f)
    
        # correct gdb feature class name
        if in_data_fc:
            g.data_fc = in_data_fc
    
    # modes
    if out_mode == "both":
        mode_arr = ["shortest", "fastest"]
    else:
        mode_arr = [out_mode]
    
    # snap
    start_end_list, snap_length, snap_time = g.snap(start, end)
    start = start_end_list[0]
    end = start_end_list[1]
    
    # algorithm
    for mode in mode_arr:
        # parameters for AShift8
        if mode == "shortest":
            cost_field = "length"
            h_funct = h_length
        elif mode == "fastest":
            cost_field = "time"
            h_funct = h_time
        
        # AShift8
        path, edge_ids, cost, vol_S = g.aShift8(cost_field, h_funct, start, end)

        # printing
        if mode == "shortest":
            print("length of the road:    ", cost / 1000, "km")
            if snap_length != 0:
                print("length of the snap:    ", snap_length, "m")
        elif mode == "fastest":
            print("time of the road:    ", cost / 60, "min")
            if snap_time != 0:
                print("time of the snap:    ", snap_time, "s")
        print("volume of S:    ", vol_S)
        print('path vertices count:', len(path))
        print('path edges count:   ', len(edge_ids))
        
        # output
        g.export_fc(edge_ids, output_name + "_" + mode)
        print("\n")

speed_dict = {'autostrada': 140, 'droga ekspresowa': 120, 'droga główna ruchu przyśpieszonego': 60, 'droga główna': 50, 'droga zbiorcza': 40, 'droga lokalna': 30, 'droga dojazdowa': 30, 'droga wewnętrzna': 20}

if __name__ == '__main__':
    # for testing
    import os, sys, time
    curr_directory = os.getcwd()
    workspace = curr_directory + r"\workspace.gdb"

    # arcpy gdb settings
    arcpy.env.workspace = workspace
    arcpy.env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference('ETRF2000-PL CS92')

    from neo4j import GraphDatabase

    # URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "HelloThere")

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
    
        summary = driver.execute_query(
            "CREATE (:Person {name: $name})",
            name="Alice",
            database_="neo4j",
        ).summary
        print("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

        # WHOLE PROCESS
        if len(sys.argv) == 1:
            t0 = time.time()
            aS8_launcher(
                out_mode="both",
                start=(479332.19, 574394.85),
                end=(476853.27, 572431.04),
                output_name="output",
                in_data_fc="SKJZ_L_Torun_m",
                create_new_graph=True,
                driver=driver
            )
            t1 = time.time()
            print("time all: ", t1-t0, "s\n")

        # GRAPH GENERATING
        elif sys.argv[1] == "g":
            t0 = time.time()
            generate_launcher(
                in_data_fc='SKJZ_L_Torun_m',
                out_graph_file="graph.pkl"
            )
            t1 = time.time()
            print("time generating: ", t1-t0, "s\n")
        
        # ALGORITHM + VISUALIZATION
        elif sys.argv[1] == "a":
            t0 = time.time()
            aS8_launcher(
                out_mode="both",
                start=(471337.576, 577701.85),
                end=(473585, 567628.5),
                output_name="output",
                in_data_fc="SKJZ_L_Torun_m",
                in_graph_file="graph.pkl",
            )
            t1 = time.time()
            print("time algorithm + visualization: ", t1-t0, "s\n")
        
    
    
