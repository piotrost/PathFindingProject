# Authors: PAGistyczna Drużyna Cybergeodetów
# Created:  2024-11-02T22:13:28.044Z

from heapdict import heapdict
import arcpy
import math
import os

class Node:
    def __init__(self):                             # no need to store node's coordinates - they are keys in "nodes" dictionary
        self.edges = []                             # keys to nodes in the "nodes dictionary" + edge info

    def add_edge(self, x, y, length, fid):
        self.edges.append(Edge(x, y, length, fid))

class Edge:
    def __init__(self, x, y, length, fid):
        self.xy = (x, y)
        self.length = length
        self.fid = fid                              # for visualization?

class Graph:
    # h function
    def h(self, start, end):                                    
        return abs(start[0] - end[0]) + abs(start[1] - end[1])

    def __init__(self, file):
        self.file = None                            # graph data source
        self.nodes = {}                             # all read data
        self.read_graph(file)
    
    def read_graph(self, file):
        with arcpy.da.SearchCursor(file, ['FID', 'SHAPE@']) as cursor:
            self.file = file                        # save graph data source path

            temp_nodes = {}                         # store the nodes' final rounded coordinates under multiple keys
            for row in cursor:
                shape = row[1]                      # only to get nodes' coordinates
                first_point = shape.firstPoint      # node
                last_point = shape.lastPoint        # second node
                fid = row[0]                        # edge fid
                length = shape.length               # edge length

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
                    
                    # all possible coordinate keys leed to the same rounded one
                    temp_nodes[xy] = xyf; temp_nodes[xy1] = xyf; temp_nodes[xy2] = xyf; temp_nodes[xy3] = xyf
                    xy_arr.append(xyf)
                
                # create edges - in two directions
                self.nodes[xy_arr[0]].add_edge(xy_arr[1][0], xy_arr[1][1], length, fid)
                self.nodes[xy_arr[1]].add_edge(xy_arr[0][0], xy_arr[0][1], length, fid)
    
    def export_graph_txt(self):
        with open("my_graph.txt", "w") as f:
            for node in self.nodes:
                f.write(f"\n\n\t<-- {node} -->\n")
                for edge in self.nodes[node].edges:
                    f.write(f"{edge.xy}\t{edge.length}\t{edge.fid}\n")
    
    def aShift8(self, start, end):
        # create data structures
        S = set(); S.add(start)
        Q = heapdict()
        p = {}; p[start] = None, None                       

        # first node's neighbours
        for edge in self.nodes[start].edges:
            future_h = self.h(edge.xy, end)
            Q[edge.xy] = edge.length + future_h, edge.length, future_h  # f, g, h for nodes added to Q - possible FUTURE S elements
            p[edge.xy] = start, edge.fid
        
        # main algorithm loop
        while Q:                                                        # ensure loop exit when no solution
            curr, (curr_f, curr_g, curr_h) = Q.popitem()                # f, g, h of CURRENT node
            
            # destination reached
            if curr == end:
                node_path = [end]; fids = []            # create output data structures
                curr = (end, None)                      # adjust curr for loop
                while curr[0] != start:
                    curr = p[curr[0]]                   # alter curr
                    node_path.append(curr[0])           # append node
                    fids.append(curr[1])                # append edge
                
                node_path.reverse(); fids.reverse()
                return node_path, fids, curr_g, len(S)
            
            # add the current node to the S set
            S.add(curr)

            for edge in self.nodes[curr].edges:
                if edge.xy not in S:
                    if edge.xy not in Q:
                        future_h = self.h(edge.xy, end)                         # h for new node - it will never be changed
                        future_g = curr_g + edge.length                         # g for new node                      
                        Q[edge.xy] = future_g + future_h, future_g, future_h    # f, g, h
                        p[edge.xy] = curr, edge.fid
                    else:
                        new_old_h = Q[edge.xy][2]                               # read Q[edge.xy][2] = old_but_up_to_date_h
                        new_g = curr_g + edge.length                            # count possibly_different_value_of_g
                        new_f = new_g + new_old_h                               # count new f based on f and g above
                        # relax the edge (if needed)
                        if new_f < Q[edge.xy][0]:                               # Q[edge.xy][0] = old_f
                            Q[edge.xy] = new_f, new_g, new_old_h                # f, g, h
                            p[edge.xy] = curr, edge.fid

if __name__ == '__main__':
    curr_directory = os.getcwd()

    # The test
    g = Graph(curr_directory + r'\data\L4_1_BDOT10k__OT_SKJZ_L.shp')
    path, fids, length, vol_s = g.aShift8((471892, 576471),(481676, 574633))
    
    # printing
    g.export_graph_txt()
    print( "volume of S:        ", vol_s)
    print("length of the road: ", length)
    print('path vertices count:', len(path))
    print('path edges count:   ', len(fids))

    # The not-a-real-visualization ############################################
    # output folder
    output_folder = curr_directory + r'\output'
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

    # add the fields to shp
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