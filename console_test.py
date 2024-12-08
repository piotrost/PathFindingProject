from ToolboxScript_Improved_v3 import *
import ToolboxScript_Improved_v3 as tb

if __name__ == '__main__':
    # *******************************************************
    # ustawienia środowiska do tworzenia aplikcaji konsolowej
    arcpy.env.workspace = r"C:\Users\piotr\Documents\pw\5\pag\PathFindingProject\workspace.gdb"
    arcpy.env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference('ETRF2000-PL CS92')
    input_file = r"C:\Users\piotr\Documents\pw\5\pag\PathFindingProject\data\nowy_SKJZ_L\torun\nowy_SKJZ_L_Torun_edited.shp"
    if ".shp" in input_file:
        tb.IDFIELD = "FID"                             # shp
    else:
        tb.IDFIELD = "OBJECTID"                        # gdb
    
    # *******************************************************
    import sys

    # WHOLE PROCESS
    if len(sys.argv) == 1:
        t0 = time.time()
        aS8_launcher(
            out_mode="Both",
            start=(479332.19, 574394.85),
            end=(476853.27, 572431.04),
            output_name="output",
            in_data_fc=input_file,
            create_new_graph=True
        )
        t1 = time.time()
        print("time all: ", t1-t0, "s\n")

    # GRAPH GENERATING
    elif sys.argv[1] == "g":
        t0 = time.time()
        generate_launcher(
            in_data_fc=input_file,
            out_graph_file="graph.pkl"
        )
        t1 = time.time()
        print("time generating: ", t1-t0, "s\n")
    
    # ALGORITHM + VISUALIZATION
    elif sys.argv[1] == "a":
        t0 = time.time()
        aS8_launcher(
            out_mode="Both",
            start=(471337.576, 577701.85),
            end=(473585, 567628.5),
            output_name="output",
            in_data_fc=input_file,
            in_graph_file="graph.pkl"
        )
        t1 = time.time()
        print("time algorithm + visualization: ", t1-t0, "s\n")