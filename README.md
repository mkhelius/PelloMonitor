Program do odczytu i sterowania palnikiem Pello 3.5 (sterownik esterownik.pl).

ZAWARTOSC FOLDERU (wszystkie pliki musza lezec razem w jednym folderze)
  pello_monitor.py   okno programu (glowny plik)
  pello_config.py    stale, kolory, teksty
  pello_client.py    komunikacja ze sterownikiem i historia CSV
  pello_tray.py      ikona plomienia, zasobnik, powiadomienia
  pello_schema.py    zakladka "Schemat instalacji"
  pello.ico          ikona pliku .exe
  build_exe.bat      buduje PelloMonitor.exe
  uruchom_program.bat  uruchamia program bez budowania .exe

WYMAGANIA
  Windows + Python 3.10 lub nowszy (python.org, przy instalacji zaznacz
  "Add Python to PATH"). Biblioteki pystray i pillow instalowane sa automatycznie.

JAK URUCHOMIC
  A) Bez budowania:  dwuklik na  uruchom_program.bat
  B) Plik .exe:      dwuklik na  build_exe.bat
                     gotowy program: dist\PelloMonitor.exe
                     (mozna go skopiowac na dowolny komputer, Python juz niepotrzebny)

PIERWSZE URUCHOMIENIE
  1. Wejdz w zakladke "Ustawienia" i wpisz adres IP sterownika (oraz login/haslo).
  2. Kliknij "Polacz" w prawym gornym rogu.
  3. Zakladki: Odczyty, Schemat instalacji, Sterowanie, Wykres, Ustawienia, Info.

PRACA W TLE
  Zamkniecie okna (X) chowa program do zasobnika przy zegarze.
  Start razem z Windows: skrot do PelloMonitor.exe --tray w folderze
  autostartu (Win+R -> shell:startup).

GDZIE SA DANE
  Ustawienia:  C:\Users\<Ty>\.pello_monitor.json
  Historia:    C:\Users\<Ty>\PelloMonitor\pello_RRRR-MM-DD.csv

WARUNKI (wersja FREE)
  Program darmowy do uzytku prywatnego i niekomercyjnego. Zakaz sprzedazy oraz
  usuwania informacji o autorze. Udostepniany "tak jak jest", bez gwarancji -
  nastawy sterownika zmieniasz na wlasna odpowiedzialnosc. Program nie jest
  oficjalnym produktem esterownik.pl.
  (c) 2026 Mariusz
