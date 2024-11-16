import arcpy


def add_columns(file, columns):
    field1 = columns[0]
    field2 = columns[1]
    field3 = columns[2]

    arcpy.management.AddField(file, field1, "TEXT")
    arcpy.management.AddField(file, field2, "TEXT")
    arcpy.management.AddField(file, field3, "TEXT")


def update_fc(inputfile):
    with arcpy.da.UpdateCursor(arcpy.env.workspace + r'\\' + inputfile,["SHAPE@", "F_POINT", "L_POINT", "DIRECTION"]) as cursor:
        for row in cursor:
            shape = row[0]
            first_point = shape.firstPoint
            first_point = "(" + str(first_point.X) + ", " + str(first_point.Y) + ")"
            row[1] = first_point
            last_point = shape.lastPoint
            last_point = "(" + str(last_point.X) + ", " + str(last_point.Y) + ")"
            row[2] = last_point
            direction = "both"
            row[3] = direction
            cursor.updateRow(row)


if __name__ == '__main__':
    arcpy.env.workspace = r"C:\pw\sem5\pag2\pag_projekt_pathfinding\workspace.gdb"
    arcpy.env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference("ETRF2000-PL CS92")

    infeature = 'nowy_SKJZ_L_Torun'
    fields = ['F_POINT', 'L_POINT', 'DIRECTION']

    add_columns(infeature, fields)
    update_fc(infeature)
