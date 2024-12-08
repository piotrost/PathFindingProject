import arcpy

# this is a 2.0 version of hi.py
print("hello world again :D")
for a in 10:
    print(a)

# ustawienia środowiska do tworzenia aplikcaji konsolowej
arcpy.env.workspace = r"C:\Ścieżka\do\dowolnej\geobazy.gdb.gdb"
arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference('ETRF2000-PL CS92')
input_file = r"C:\Ścieżka\do\danych\wejściowych.shp"
if ".shp" in input_file:
    IDFIELD = "FID"                             # shp
else:
    IDFIELD = "OBJECTID"                        # gdb