# PathFindingProject
PAG 2024Z

# 11.10.
networksx python library - może my będziemy pierwsi XD - choć chyba ne ma po co

geofabrik.de / qgis - osm

3 zbiory danych - np. duże miasto / województwo, mały zbiór(np. wycinek miasta), kolejny zbiór schematyczny, możemy sobie sami narysować(do śledzenia algorytmu)

arcgis / temat 4

# 25.10.
dane można wciągnąć z ArcGISa do grafu kursorem. - pętelka for
na przykład: id, klasadrogi, Shape.length, Shape.WKT
albo raczej: fid, length, firstPoint, lastPoint - coś jakby struktura grafowa

dodawanie krawędzi i w razie potrzeby tworzenie nowych wierzchołków - w danych źródłowych tylko krawędzie - ale to wierzcholki trzymają w listach sąsiedztwa krawędzie
index mapujący geometrię punktu na index?
słownik x,y - id
id tekstowe, które będą geometrią - nie potrzeba tablicy
niespójna geometria - zaokrąglajmy do kilku metrów / najbliższej liczby całkowitej już przy tworzeniu id
indeksjemy czterema geometriami - wszystkie kombinacje w górę / w dół
tworzenie grafu nie jest takie hop siup

wierzchołek - funkcja get neighbours
trzymać czas i długość - nie tajemniczy koszt?
kolejka priorytetowa - pobawimy się osobno
tablica, czy dictionary - ważne
kolejka priorytetowa pythona nie zmienia priorytetu - a my musimy zmieniać przy relaksacji wierzchołków - własna kolejka, albo przerobić algorytm A*, by wspierał elementy wielokrotnie włożone do środka