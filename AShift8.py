# Authors: PAGistyczna Drużyna Cybergeodetów
# Created:  2024-11-02T22:13:28.044Z

from heapdict import heapdict
import arcpy
import math
import os

class Node:
    def __init__(self):             # no need to store node's coordinates - they are keys in 'nodes' dictionary
        self.edges = []             # keys to nodes in the nodes dictionary + edge info

    def add_edge(self, x, y, length, fid):
        self.edges.append(Edge(x, y, length, fid))

class Edge:
    def __init__(self, x, y, length, fid):
        self.xy = (x, y)
        self.length = length
        self.fid = fid              # for visualization?

class Graph:
    # heuristic function
    def h(self, start, end):                                    
        return abs(start[0] - end[0]) + abs(start[1] - end[1])

    def __init__(self, file):
        self.file = None
        self.nodes = {}
        self.read_graph(file)
    
    def read_graph(self, file):
        with arcpy.da.SearchCursor(file, ['FID', 'SHAPE@']) as cursor:
            self.file = file    # graph file path
            # store the nodes' final rounded coordinates under multiple keys
            temp_nodes = {}
            for row in cursor:
                shape = row[1]
                first_point = shape.firstPoint
                last_point = shape.lastPoint
                fid = row[0]
                length = shape.length

                xy_arr = [] # final nodes' coordinates
                for point in [first_point, last_point]:
                    coords = (point.X, point.Y)
                    # round the coordinates in all possible ways
                    xy = (math.floor(coords[0]), math.ceil(coords[1]))
                    xy1 = (math.ceil(coords[0]), math.floor(coords[1]))
                    xy2 = (math.floor(coords[0]), math.floor(coords[1]))
                    xy3 = (math.ceil(coords[0]), math.ceil(coords[1]))
                
                    if xy in temp_nodes:
                        xyf = temp_nodes[xy]            # get the final rounded coordinates
                    elif xy1 in temp_nodes:
                        xyf = temp_nodes[xy1]           # -----||-----
                    elif xy2 in temp_nodes:
                        xyf = temp_nodes[xy2]           # -----||-----
                    elif xy3 in temp_nodes:
                        xyf = temp_nodes[xy3]           # -----||-----
                    else:
                        self.nodes[xy] = Node()         # create a new node
                        xyf = xy
                    
                    # all possible coordinate keys leed to the same rounded one
                    temp_nodes[xy] = xyf; temp_nodes[xy1] = xyf; temp_nodes[xy2] = xyf; temp_nodes[xy3] = xyf
                    xy_arr.append(xyf)
                
                # create edges - in two directions
                self.nodes[xy_arr[0]].add_edge(xy_arr[1][0], xy_arr[1][1], length, fid)
                self.nodes[xy_arr[1]].add_edge(xy_arr[0][0], xy_arr[0][1], length, fid)
    
    def export_graph_txt(self):
        with open("my_graph.txt", "w") as f:
            for node in self.nodes:
                f.write(f"\n\n\t--> {node}\n")
                for edge in self.nodes[node].edges:
                    f.write(f"{edge.xy}\t{edge.length}\t{edge.fid}\n")
    
    def aShift8(self, start, end):
        S = set(); S.add(start)
        Q = heapdict()
        p = {}; p[start] = None, None                       # previous_node, previous_edge_fid

        for edge in self.nodes[start].edges:
            h_edge = self.h(edge.xy, end)
            Q[edge.xy] = edge.length + h_edge, h_edge       # whole_length, heuristic - the goal of storing heurisctic is to count it only once
            p[edge.xy] = start, edge.fid
        
        # ensure loop exit when no solution
        while Q:
            curr, (c_length, c_h) = Q.popitem()     # current_xy, (current_length_with_heuristic, current_heuristic)
            c_length -= c_h                         # current length without heuristic - this could also be held as another atribute in Q, but is this the way???
            
            # if the goal is reached
            if curr == end:
                node_path = [end]; fids = []
                curr = (end, None)
                while curr[0] != start:
                    curr = p[curr[0]]
                    node_path.append(curr[0])
                    fids.append(curr[1])
                
                node_path.reverse(); fids.reverse()
                return node_path, fids, c_length, len(S)
            
            # add the current node to the S set
            S.add(curr)

            for edge in self.nodes[curr].edges:
                if edge.xy not in S:
                    if edge.xy not in Q:
                        # count the heuristic - only once
                        h_edge = self.h(edge.xy, end)                           
                        Q[edge.xy] = c_length + edge.length + h_edge, h_edge    # whole_path_length + heuristic, heuristic
                        p[edge.xy] = curr, edge.fid
                    else:
                        new_length = c_length + edge.length + Q[edge.xy][1]     # Q[edge.xy][1] - already counted heuristic
                        # relax the edge (if needed)
                        if new_length < Q[edge.xy][0]:
                            Q[edge.xy] = new_length, Q[edge.xy][1]    
                            p[edge.xy] = curr, edge.fid

if __name__ == '__main__':
    current_directory = os.getcwd()
    g = Graph(current_directory + r'\data\L4_1_BDOT10k__OT_SKJZ_L.shp')
    path, fids, length, vol_s = g.aShift8((471892, 576471),(481676, 574633))
    g.export_graph_txt()
    print( "volume of S:        ", vol_s)
    print("length of the road: ", length)
    print('path vertices count:', len(path))
    print('path edges count:   ', len(fids))

    # The not-a-real-visualization ############################################
    # output folder
    output_folder = current_directory + r'\output'
    for filename in os.listdir(output_folder):
        file_path = os.path.join(output_folder, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    # input shp
    input_shp = g.file

    # output shp
    output_shp = output_folder + r'\output.shp'

    # the same geometry and crs as the input
    arcpy.CreateFeatureclass_management(
        os.path.dirname(output_shp),
        os.path.basename(output_shp),
        arcpy.Describe(input_shp).shapeType,
        spatial_reference=arcpy.Describe(input_shp).spatialReference
    )

    # new fields
    field_names = ["EDGE_FID","F_POINT", "L_POINT"]
    field_types = ["INTEGER", "TEXT", "TEXT"]

    # Add the fields to shp
    for field_name, field_type in zip(field_names, field_types):
        arcpy.AddField_management(output_shp, field_name, field_type)

    # copying
    with arcpy.da.SearchCursor(input_shp, ["FID", "SHAPE@"]) as cursor:
        with arcpy.da.InsertCursor(output_shp, ["EDGE_FID","F_POINT", "L_POINT", "SHAPE@"]) as insert_cursor:
            for row in cursor:
                if row[0] in fids:
                    fid = row[0]
                    shape = row[1]
                    first_point = shape.firstPoint
                    first_point = "(" + str(first_point.X) + ", " + str(first_point.Y) + ")"
                    last_point = shape.lastPoint
                    last_point = "(" + str(last_point.X) + ", " + str(last_point.Y) + ")"

                    insert_cursor.insertRow([fid, first_point, last_point, shape])

    print("Creating a stupid shp instead of a proper visualization completed.")