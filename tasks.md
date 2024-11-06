->  Ocena dostateczna (konieczne do zaliczenia ćwiczenia):
# Implementacja algorytmów Dijkstra i A* niezależnie od złożoności czasowej
1. jeszcze Djikstra teoretycznie
* Odczyt sieci drogowej z wybranego źródła
* Utworzenie grafu na podstawie sieci drogowej
* Eliminacja problemów z niespójną geometrią
* Uruchomienie wyznaczania trasy dla sieci drogowej
# Wyznaczanie trasy najkrótszej i najszybszej
1. jeszcze najszybsza: (klasadrogi na prędkość) * czas
# Raport końcowy

-------------------------------------------------------------------------------------------------
->  Ocena dobra
# Prezentacja wyników w środowisku GIS
1. jak zaznaczyć trasę i punkty na istniejącej wcześniej warstwie / dodanie nowowygenreowanej warstwy wektorowej i w miarę możliwości ustawienie symbolizacji
2. ? trzymać prawdziwą geometrię krawędzi w strukturze grafu?
# Uwzględnienie kierunkowości dróg przy wyznaczaniu trasy
1. łatwe, ale skąd dane o kierunkowości
# Implementacja algorytmów wyznaczania trasy z akceptowalną złożonością czasową, w tym wykorzystanie koleki priorytetowej
1. kolejka jest, ale badania złożoności brak

-------------------------------------------------------------------------------------------------
->  Ocena bardzo dobra
# Implementacja rozszerzenia
1. BFS, ewentualnie DFS z warunkiem stopu
2. jak ostatecznie wyznaczyć punkty zasięgu
# Możliwość wybory przez użytkownika punktu początkowego i końcowego z mapy
# Automatyzacja procesu wyświetlania wyniku (proces nie musi być zintegrowany ze środowiskiem GIS jak w przypadku add-in, ale po jego wykonaniu trasa powinna się wyświetlać).
1. script tool w arcgisie
