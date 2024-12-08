from ToolboxScript_Improved_v3 import *
import ToolboxScript_Improved_v3 as tb

class NewGraph(Graph):
    def dijkstra(self, cost, start, end):
            # deklaracja struktur danych
            S = set()                                           # zbiór odwiedzonych węzłów
            S.add(start)
            Q = heapdict()                                      # kolejka priorytetowa sąsiadów odwiedzonych węzłów
            p = {start: (None, None)}                           # słownik poprzedników
            
            # sąsiedzi pierwszego węzła
            for edge in self.nodes[start].edges:
                Q[edge.id] = getattr(edge, cost)
                p[edge.id] = start, edge.edge_id                # dodanie poprzednika i id prowadzącej do niego krawędzi
            
            # główna pętla
            while Q:                                            # wyjście z pętli w razie nieznalezienia ścieżki
                curr, curr_g = Q.popitem()                      # g dla bieżącego węzła
                
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
                            future_g = curr_g + getattr(edge, cost)                         # g dla węzła na końcu krawędzi
                            Q[edge.id] = future_g                                           # dodanie g dla węzła na końcu krawędzi
                            p[edge.id] = curr, edge.edge_id
                        else:
                            new_g = curr_g + getattr(edge, cost)                            # nowa wartość g
                            
                            # relaksacja krawędzi
                            if new_g < Q[edge.id]:                                          # Q[edge.xy][0] = stara wartość f
                                Q[edge.id] = new_g                                          # g
                                p[edge.id] = curr, edge.edge_id

def generate_launcher(in_data_fc, out_graph_file="graph.pkl"):
    # utworzenie grafu
    g = NewGraph(in_data_fc)
    
    # zapis przy pomocy biblioteki pickle
    with open(out_graph_file, 'wb') as f:
        pickle.dump(g, f)

def aS8_launcher(out_mode, start, end, output_name="PF", in_data_fc=None, in_graph_file="graph.pkl", create_new_graph=False):
    # tworzenie nowego grafu
    if create_new_graph:
        g = NewGraph(in_data_fc)
    else:
        # odczyt grafu z pliku pickle
        with open(in_graph_file, 'rb') as f:
            g: NewGraph = pickle.load(f)
        
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

        if mode == "Fastest_Path":
            with open("as8_fast.csv", "a") as f:
                f.write(f"{len(path)},{vol_S},{t_alg_1 - t_alg_0},{cost / 60}\n")
        elif mode == "Shortest_Path":
            with open("as8_short.csv", "a") as f:
                f.write(f"{len(path)},{vol_S},{t_alg_1 - t_alg_0},{cost / 1000}\n")
        
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

def dijkstra_launcher(out_mode, start, end, output_name="PF", in_data_fc=None, in_graph_file="graph.pkl", create_new_graph=False):
    # tworzenie nowego grafu
    if create_new_graph:
        g = NewGraph(in_data_fc)
    else:
        # odczyt grafu z pliku pickle
        with open(in_graph_file, 'rb') as f:
            g: NewGraph = pickle.load(f)
        
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
    
    # dijkstra
    for mode in mode_arr:
        # parametry dla aktualnego trybu
        if mode == "Shortest_Path":
            cost_field = "length"
        elif mode == "Fastest_Path":
            cost_field = "time"
        
        # Dijkstra
        t_alg_0 = time.time()
        path, edge_ids, cost, vol_S = g.dijkstra(cost_field, start, end)
        t_alg_1 = time.time()
        arc_prnt(f"Time of {mode} Dijkstra algorithm: {t_alg_1 - t_alg_0} s")

        if mode == "Fastest_Path":
            with open("dijkstra_fast.csv", "a") as f:
                f.write(f"{len(path)},{vol_S},{t_alg_1 - t_alg_0},{cost / 60}\n")
        elif mode == "Shortest_Path":
            with open("dijkstra_short.csv", "a") as f:
                f.write(f"{len(path)},{vol_S},{t_alg_1 - t_alg_0},{cost / 1000}\n")
        
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


if __name__ == '__main__':
    import sys, os
    # *******************************************************
    # ustawienia środowiska do tworzenia aplikcaji konsolowej
    arcpy.env.workspace = str(os.getcwd()) + "\\workspace.gdb"
    arcpy.env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference('ETRF2000-PL CS92')
    input_file = str(os.getcwd()) + "\\data\\nowy_SKJZ_L\\torun\\nowy_SKJZ_L_Torun_edited.shp"
    if ".shp" in input_file:
        tb.IDFIELD = "FID"                             # shp
    else:
        tb.IDFIELD = "OBJECTID"                        # gdb
    
    # *******************************************************
    
    test_1 = str(os.getcwd()) + "\\data\\test\\test_1.shp"
    test_2 = str(os.getcwd()) + "\\data\\test\\test_2.shp"

    list_1 = []
    list_2 = []

    with arcpy.da.SearchCursor(test_1, ["SHAPE@"]) as cursor:
        for row in cursor:
            shape = row[0]
            xy = (shape.firstPoint.X, shape.firstPoint.Y)
            list_1.append(xy)
    
    with arcpy.da.SearchCursor(test_2, ["SHAPE@"]) as cursor:
        for row in cursor:
            shape = row[0]
            xy = (shape.firstPoint.X, shape.firstPoint.Y)
            list_2.append(xy)

    # GRAPH GENERATING
    t0 = time.time()
    generate_launcher(
        in_data_fc=input_file,
        out_graph_file="graph.pkl"
    )
    t1 = time.time()
    print("time generating: ", t1-t0, "s\n")

    # ALGORITHM + VISUALIZATION
    for point_1 in list_1:
        for point_2 in list_2:
            # AShift8
            t0 = time.time()
            aS8_launcher(
                out_mode="Both",
                start=point_1,
                end=point_2,
                output_name="output",
                in_data_fc=input_file,
                in_graph_file="graph.pkl"
            )
            t1 = time.time()
            print("AShift8 time algorithm + visualization: ", t1-t0, "s\n")

            # Dijkstra
            t0 = time.time()
            dijkstra_launcher(
                out_mode="Both",
                start=point_1,
                end=point_2,
                output_name="output",
                in_data_fc=input_file,
                in_graph_file="graph.pkl"
            )
            t1 = time.time()
            print("Dijkstra time algorithm + visualization: ", t1-t0, "s\n")