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
    def __init__(self, data_fc, nodes_fc):
        self.data_fc = data_fc                        # graph source line fc name
        self.nodes_fc = nodes_fc                      # nodes for snapping fc name
        self.nodes = {}                               # the nodes - core data structure for A*
        self.generate_graph()
    
    def generate_graph(self):
        # create output nodes feature class in gdb - for snapping only
        arcpy.management.CreateFeatureclass(arcpy.env.workspace, self.nodes_fc, 'POINT')

        # create graph
        with arcpy.da.SearchCursor(arcpy.env.workspace + "\\" + self.data_fc, ["OBJECTID", "SHAPE@", 'KLASA_DROG']) as cursor:
            with arcpy.da.InsertCursor(arcpy.env.workspace + "\\" + self.nodes_fc, ["SHAPE@"]) as insert_cursor:
                temp_nodes = {}                         # store the nodes' final rounded coordinates under multiple keys
                
                for row in cursor:
                    edge_id = row[0]                    # edge OBJECTID   
                    shape = row[1]                      # edge geometry

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
                                xyf = xy                            # set final rounded coordinates
                                insert_cursor.insertRow([point])    # insert the node into gdb
                        
                        # all possible coordinate keys leed to the same rounded one
                        temp_nodes[xy] = xyf; temp_nodes[xy1] = xyf; temp_nodes[xy2] = xyf; temp_nodes[xy3] = xyf
                        xy_arr.append(xyf)
                    
                    # edge time
                    time = length / (speed * 1000/3600)

                    # create edges - in two directions and in gdb
                    self.nodes[xy_arr[0]].add_edge(xy_arr[1][0], xy_arr[1][1], edge_id, length, time)
                    self.nodes[xy_arr[1]].add_edge(xy_arr[0][0], xy_arr[0][1], edge_id, length, time)
    
        arcpy.management.AddSpatialIndex(self.nodes_fc)

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
            # create output feature class in gdb
            arcpy.management.CreateFeatureclass(arcpy.env.workspace, name, 'POLYLINE')
            
            # new fields
            field_names = ["EDGE_ID","F_POINT", "L_POINT"]
            field_types = ["INTEGER", "TEXT", "TEXT"]

            # add the fields to feature class
            for field_name, field_type in zip(field_names, field_types):
                arcpy.AddField_management(name, field_name, field_type)

            # copying
            with arcpy.da.SearchCursor(self.data_fc, ["OBJECTID", "SHAPE@"]) as cursor:
                with arcpy.da.InsertCursor(arcpy.env.workspace + r'\\' + name, ["EDGE_ID","F_POINT", "L_POINT", "SHAPE@"]) as insert_cursor:
                    for row in cursor:
                        if row[0] in oids:
                            edge_id = row[0]
                            shape = row[1]
                            first_point = shape.firstPoint
                            first_point = "(" + str(first_point.X) + ", " + str(first_point.Y) + ")"
                            last_point = shape.lastPoint
                            last_point = "(" + str(last_point.X) + ", " + str(last_point.Y) + ")"
                            
                            insert_cursor.insertRow([edge_id, first_point, last_point, shape])

            print(f"Creating feature class '{name}'.")
    
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
            # create unsnapped_points temporary fc
            arcpy.management.CreateFeatureclass(arcpy.env.workspace, "ends_outside_graph", 'POINT')
            with arcpy.da.InsertCursor("ends_outside_graph", ["SHAPE@"]) as insert_cursor:
                for point in outside_graph:
                    insert_cursor.insertRow([arcpy.Point(point[0], point[1])])
            
            # find the nearest nodes
            arcpy.analysis.Near("ends_outside_graph", self.nodes_fc, 500, "LOCATION")

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
                        shape = row[0]
                        near_x = row[1]; near_y = row[2]
                        
                        line = arcpy.Polyline(arcpy.Array([arcpy.Point(shape[0], shape[1]), arcpy.Point(near_x, near_y)]))
                        insert_cursor.insertRow(["(" + str(shape[0]) + "," + str(shape[1]) + ")" , str(cr), line])
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

def generate_launcher(in_data_fc, out_nodes_fc='nodes', out_graph_file="graph.pkl"):
    # create graph
    g = Graph(in_data_fc, out_nodes_fc)

    # save graph with pickle
    with open(out_graph_file, 'wb') as f:
        pickle.dump(g, f)

def aS8_launcher(out_mode, start, end, output_name = "output", in_data_fc=None, nodes_fc=None, in_graph_file="graph.pkl", create_new_graph=False):
    if create_new_graph:
        if nodes_fc == None:
            nodes_fc = "nodes"
        g = Graph(in_data_fc, nodes_fc)
    else:
        # read graph with pickle
        with open(in_graph_file, 'rb') as f:
            g: Graph = pickle.load(f)
    
        # correct gdb feature classes names if needed
        if in_data_fc:
            g.data_fc = in_data_fc
        if nodes_fc:
            g.nodes_fc = nodes_fc
    
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

    # WHOLE PROCESS
    if len(sys.argv) == 1:
        t0 = time.time()
        aS8_launcher(
            out_mode="both",
            start=(471337.576, 577701.85),
            end=(473585, 567628.5),
            output_name="output",
            in_data_fc="SKJZ_L_Torun_m",
            create_new_graph=True
        )
        t1 = time.time()
        print("time all: ", t1-t0, "s\n")

    # GRAPH GENERATING
    elif sys.argv[1] == "g":
        t0 = time.time()
        generate_launcher(
            in_data_fc='SKJZ_L_Torun_m',
            out_nodes_fc='nodes',
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
            nodes_fc="nodes",
            in_graph_file="graph.pkl"
        )
        t1 = time.time()
        print("time algorithm + visualization: ", t1-t0, "s\n")
        
    
    
