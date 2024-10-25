import arcpy


class Vertex:
    def __init__(self, x, y):
        self.coordinates = (round(x), round(y))
        self.road_ids = set()

    def add_road_id(self, road_id):
        self.road_ids.add(road_id)

    def __repr__(self):
        return f"Vertex: {self.coordinates}, Road IDs: {self.road_ids}"


class Road:
    def __init__(self, road_id):
        self.road_id = road_id
        self.vertices = []
        self.length = 0  # Inicjalizujemy długość drogi

    def add_vertex(self, vertex):
        self.vertices.append(vertex)

    def set_length(self, length):
        self.length = length

    def get_vertex_ids(self):
        return [vertex.coordinates for vertex in self.vertices]

    def __repr__(self):
        return f"Road ID: {self.road_id}, Vertex IDs: {self.get_vertex_ids()}, Length: {self.length}"


class VertexManager:
    def __init__(self, shapefile_path):
        self.shapefile_path = shapefile_path
        self.vertices = {}
        self.roads = {}

    def extract_data(self):
        with arcpy.da.SearchCursor(self.shapefile_path, ['FID', 'SHAPE@']) as cursor:
            for row in cursor:
                fid = row[0]
                shape = row[1]
                first_point = shape.firstPoint
                last_point = shape.lastPoint

                # Sprawdź i dodaj pierwszy punkt
                self._add_vertex(first_point.X, first_point.Y, fid)
                # Sprawdź i dodaj ostatni punkt
                self._add_vertex(last_point.X, last_point.Y, fid)

                # Utwórz lub zaktualizuj drogę
                if fid not in self.roads:
                    self.roads[fid] = Road(fid)

                # Dodaj wierzchołki do drogi
                self.roads[fid].add_vertex(self.vertices[(round(first_point.X), round(first_point.Y))])
                self.roads[fid].add_vertex(self.vertices[(round(last_point.X), round(last_point.Y))])

                # Ustaw długość drogi
                self.roads[fid].set_length(shape.length)

    def _add_vertex(self, x, y, fid):
        key = (round(x), round(y))
        if key not in self.vertices:
            self.vertices[key] = Vertex(x, y)
        self.vertices[key].add_road_id(fid)

    def get_vertices(self):
        return self.vertices

    def get_roads(self):
        return self.roads


# Ustaw ścieżkę do pliku shapefile
shapefile_path = "L4_1_BDOT10k__OT_SKJZ_L"

# Utwórz menedżera wierzchołków i wyciągnij dane
vertex_manager = VertexManager(shapefile_path)
vertex_manager.extract_data()

print("Vertices:")
for vertex in vertex_manager.get_vertices().values():
    print(vertex)

# Wyświetl drogi
print("\nRoads:")
for road in vertex_manager.get_roads().values():
    print(road)
