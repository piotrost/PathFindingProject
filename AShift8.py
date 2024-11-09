# Authors: PAGistyczna Drużyna Cybergeodetów
# Created:  2024-11-02T22:13:28.044Z

from heapdict import heapdict
import arcpy
import math
import os

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
    return math.sqrt((current[0] - end[0])**2 + (current[1] - end[1])**2) / 38.889 # / (140 * 1000 / 3600) ~ 38.(8)

class Graph:
    def __init__(self, file):
        self.file = None                            # graph data source
        self.nodes = {}                             # the nodes - core data structure for A*
        self.read_graph(file)
    
    def read_graph(self, file):
        # create output feature class in gdb
        arcpy.management.CreateFeatureclass(arcpy.env.workspace, 'nodes', 'POINT')
        
        # new fields
        field_names = ["ID"]
        field_types = ["TEXT"]

        # add the fields to feature class
        for field_name, field_type in zip(field_names, field_types):
            arcpy.AddField_management('nodes', field_name, field_type)

        # copying
        with arcpy.da.SearchCursor(arcpy.env.workspace + "\\" + file, ["OBJECTID", "SHAPE@", 'klasaDrogi']) as cursor:
            with arcpy.da.InsertCursor(arcpy.env.workspace + r'\nodes', ["ID", "SHAPE@"]) as insert_cursor:
                self.file = file                        # save graph data source path / feature class
                temp_nodes = {}                         # store the nodes' final rounded coordinates under multiple keys
                
                for row in cursor:
                    edge_id = row[0]                    # edge OBJECTID   
                    shape = row[1]                      # edge geometry

                    first_point = shape.firstPoint      # node
                    last_point = shape.lastPoint        # second node
                    length = shape.length               # edge length
                    speed = speed_dict.get(row[2])

                    xy_arr = []                         # final nodes' coordinates
                    
                    for point in [first_point, last_point]:
                        # raw coordinates
                        coords = (point.X, point.Y)
                        
                        # round the coordinates in all possible ways
                        xy = (math.floor(coords[0]), math.ceil(coords[1]))
                        xy1 = (math.ceil(coords[0]), math.floor(coords[1]))
                        xy2 = (math.floor(coords[0]), math.floor(coords[1]))
                        xy3 = (math.ceil(coords[0]), math.ceil(coords[1]))
                    
                        if xy in temp_nodes:
                            xyf = temp_nodes[xy]        # get the final rounded coordinates
                        elif xy1 in temp_nodes:
                            xyf = temp_nodes[xy1]       # -----||-----
                        elif xy2 in temp_nodes:
                            xyf = temp_nodes[xy2]       # -----||-----
                        elif xy3 in temp_nodes:
                            xyf = temp_nodes[xy3]       # -----||-----
                        else:
                            self.nodes[xy] = Node()     # create a new node
                            xyf = xy                    # set final rounded coordinates
                            
                            # insert the node into gdb
                            insert_cursor.insertRow([str(xyf), point])
                        
                        # all possible coordinate keys leed to the same rounded one
                        temp_nodes[xy] = xyf; temp_nodes[xy1] = xyf; temp_nodes[xy2] = xyf; temp_nodes[xy3] = xyf
                        xy_arr.append(xyf)
                    
                    # edge time
                    time = length / (speed * 1000/3600)

                    # create edges - in two directions and in gdb
                    self.nodes[xy_arr[0]].add_edge(xy_arr[1][0], xy_arr[1][1], edge_id, length, time)
                    self.nodes[xy_arr[1]].add_edge(xy_arr[0][0], xy_arr[0][1], edge_id, length, time)
    
        arcpy.management.AddSpatialIndex('nodes')

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
            with arcpy.da.SearchCursor(self.file, ["OBJECTID", "SHAPE@"]) as cursor:
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

speed_dict = {'A': 140, 'S': 120, 'GP': 60, 'G': 50, 'Z': 40, 'L': 30, 'D': 30, 'I': 20}

if __name__ == '__main__':
    curr_directory = os.getcwd()

    # testing
    import time

    # arcpy gdb settings
    arcpy.env.workspace = curr_directory + r"\workspace.gdb"
    arcpy.env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference("ETRF2000-PL CS92")

    # reading
    tr0 = time.time()
    g = Graph('SKJZ_L_Torun_m')
    tr1 = time.time()
    print("reading: ", tr1-tr0, "s\n")
    
    # algorithm shortest
    t0 = time.time()
    path, edge_ids, cost, vol_S = g.aShift8("length", h_length, (471892, 576471),(481676, 574633))
    t1 = time.time()
    print("algorithm shortest: ", t1-t0, "s")
    print( "volume of S:        ", vol_S)
    print("length of the road: ", cost / 1000, "km")
    print('path vertices count:', len(path))
    print('path edges count:   ', len(edge_ids))
    g.export_fc(edge_ids, "output_shortest")
    print("\n")

    # algorithm fastest
    t0 = time.time()
    path, edge_ids, cost, vol_S = g.aShift8("time", h_time, (471892, 576471),(481676, 574633))
    t1 = time.time()
    print("algorithm fastest:  ", t1-t0, "s")
    print( "volume of S:        ", vol_S)
    print("time of the road:   ", cost / 60, "min")
    print('path vertices count:', len(path))
    print('path edges count:   ', len(edge_ids))
    g.export_fc(edge_ids, "output_fastest")
    print("\n")
    
    # export graph to txt
    g.export_graph_txt()
    
    
    