from heapdict import heapdict
import arcpy
import math
import os


class Node:
    def __init__(self):  
        self.edges = []  

    def add_edge(self, x, y, length, fid, road_speed):
        self.edges.append(Edge(x, y, length, fid, road_speed))


class Edge:
    def __init__(self, x, y, length, fid, road_speed):
        self.xy = (x, y)
        self.length = length
        self.fid = fid 
        self.road_speed = road_speed

    def h(self, end):
        return abs(self.xy[0] - end[0]) + abs(self.xy[1] - end[1])


class Graph:
    def __init__(self, file):
        self.file = None  
        self.nodes = {} 
        self.read_graph(file)

    def read_graph(self, file):
        with arcpy.da.SearchCursor(file, ['FID', 'SHAPE@', 'klasaDrogi']) as cursor:
            self.file = file  

            temp_nodes = {}  
            for row in cursor:
                shape = row[1] 
                speed = speed_dict.get(row[2])
                first_point = shape.firstPoint  
                last_point = shape.lastPoint 
                fid = row[0]  
                length = shape.length   

                xy_arr = []   

                for point in [first_point, last_point]:
                    coords = (point.X, point.Y)

                    xy = (math.floor(coords[0]), math.ceil(coords[1]))
                    xy1 = (math.ceil(coords[0]), math.floor(coords[1]))
                    xy2 = (math.floor(coords[0]), math.floor(coords[1]))
                    xy3 = (math.ceil(coords[0]), math.ceil(coords[1]))

                    if xy in temp_nodes:
                        xyf = temp_nodes[xy]  
                    elif xy1 in temp_nodes:
                        xyf = temp_nodes[xy1]  
                    elif xy2 in temp_nodes:
                        xyf = temp_nodes[xy2] 
                    elif xy3 in temp_nodes:
                        xyf = temp_nodes[xy3]
                    else:
                        self.nodes[xy] = Node()  
                        xyf = xy

                    temp_nodes[xy] = xyf
                    temp_nodes[xy1] = xyf
                    temp_nodes[xy2] = xyf
                    temp_nodes[xy3] = xyf
                    xy_arr.append(xyf)

                self.nodes[xy_arr[0]].add_edge(xy_arr[1][0], xy_arr[1][1], length, fid, speed)
                self.nodes[xy_arr[1]].add_edge(xy_arr[0][0], xy_arr[0][1], length, fid, speed)

    def export_graph_txt(self):
        with open("my_graph.txt", "w") as f:
            for node in self.nodes:
                f.write(f"\n\n\t<-- {node} -->\n")
                for edge in self.nodes[node].edges:
                    f.write(f"{edge.xy}\t{edge.length}\t{edge.fid}\t{edge.road_speed}\n")

    def aShift8(self, start, end):
        S = set()
        S.add(start)
        Q = heapdict()
        p = {start: (None, None)}

        for edge in self.nodes[start].edges:
            future_h = edge.h(end) / (edge.road_speed * 1000 / 3600)
            travel_time = edge.length / (edge.road_speed * 1000/3600)
            Q[edge.xy] = travel_time + future_h, travel_time, future_h  
            p[edge.xy] = start, edge.fid

        while Q:   
            curr, (curr_f, curr_g, curr_h) = Q.popitem()  
            
            if curr == end:
                node_path = [end]
                fids = [] 
                curr = (end, None)   
                while curr[0] != start:
                    curr = p[curr[0]] 
                    node_path.append(curr[0])   
                    fids.append(curr[1])  
                node_path.reverse()
                fids.reverse()
                return node_path, fids, curr_g, len(S)
            S.add(curr)

            for edge in self.nodes[curr].edges:
                if edge.xy not in S:
                    travel_time = edge.length / (edge.road_speed * 1000/3600)
                    future_h = edge.h(end) / (edge.road_speed * 1000 / 3600)
                    if edge.xy not in Q:
                        future_g = curr_g + travel_time  
                        Q[edge.xy] = future_g + future_h, future_g, future_h  
                        p[edge.xy] = curr, edge.fid
                    else:
                        new_old_h = Q[edge.xy][2]   
                        new_g = curr_g + travel_time  
                        new_f = new_g + new_old_h 
                        if new_f < Q[edge.xy][0]:
                            Q[edge.xy] = new_f, new_g, new_old_h
                            p[edge.xy] = curr, edge.fid


speed_dict = {'A': 140, 'S': 120, 'GP': 60, 'G': 50, 'Z': 40, 'L': 30, 'D': 30, 'I': 20}

if __name__ == '__main__':
    curr_directory = os.getcwd()

    g = Graph(curr_directory + r'\dane\L4_1_BDOT10k__OT_SKJZ_L.shp')
    path, fids, duration, vol_s = g.aShift8((474243, 574767),(474903, 570456))

    g.export_graph_txt()
    print("volume of S:        ", vol_s)
    print("duration of the road (in mins): ", duration/60)
    print('path vertices count:', len(path))
    print('path edges count:   ', len(fids))

    output_folder = curr_directory + r'\output'
    # for filename in os.listdir(output_folder):
    #     file_path = os.path.join(output_folder, filename)
    #     if os.path.isfile(file_path):
    #         os.remove(file_path)

    input_shp = g.file
    output_shp = output_folder + r'\output_fastest.shp'

    arcpy.CreateFeatureclass_management(
        os.path.dirname(output_shp),
        os.path.basename(output_shp),
        arcpy.Describe(input_shp).shapeType,
        spatial_reference=arcpy.Describe(input_shp).spatialReference
    )

    field_names = ["EDGE_FID", "F_POINT", "L_POINT", "TIME_SEC"]
    field_types = ["INTEGER", "TEXT", "TEXT", "FLOAT"]

    for field_name, field_type in zip(field_names, field_types):
        arcpy.AddField_management(output_shp, field_name, field_type)

    with arcpy.da.SearchCursor(input_shp, ["FID", "SHAPE@", "klasaDrogi"]) as cursor:
        with arcpy.da.InsertCursor(output_shp, ["EDGE_FID", "F_POINT", "L_POINT", "TIME_SEC", "SHAPE@"]) as insert_cursor:
            for row in cursor:
                if row[0] in fids:
                    fid = row[0]
                    shape = row[1]
                    duration = shape.length / speed_dict.get(row[2]) * 1000/3600
                    first_point = shape.firstPoint
                    first_point = "(" + str(first_point.X) + ", " + str(first_point.Y) + ")"
                    last_point = shape.lastPoint
                    last_point = "(" + str(last_point.X) + ", " + str(last_point.Y) + ")"

                    insert_cursor.insertRow([fid, first_point, last_point, duration, shape])

    print("Creating a shapefile.")
