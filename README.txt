PELLO MONITOR - wersja FREE 3.4   (sterowniki Pello 3.5 i Pello D, esterownik.pl)
Autor: Mariusz  |  e-mail: mk.helius@gmail.com
=========================================================================

Program do odczytu i sterowania sterownikiem Pello z komputera z Windows.

ZAWARTOŚĆ FOLDERU (wszystkie pliki muszą leżeć razem w jednym folderze)
  pello_monitor.py     okno programu (główny plik)
  pello_config.py      stałe, kolory, teksty
  pello_params.py      katalog wszystkich parametrów sterownika (opisy, jednostki, grupy)
  pello_client.py      komunikacja ze sterownikiem, weryfikacja zapisu, historia CSV
  pello_secret.py      bezpieczne przechowywanie hasła
  pello_backup.py      logika kopii zapasowych ustawień
  pello_backup_view.py zakładka "Kopie"
  pello_locks.py       parametry zablokowane na stałe (sieć, czas, tożsamość, serwis, spalanie ...)
  pello_edit.py        zasady edycji parametrów (ryzyko, walidacja)
  pello_dialogs.py     jednolite okienka programu
  pello_edit_view.py   okno edycji parametru i dziennik zmian (zakładka "Parametry")
  pello_journal.py     zapis dziennika zmian
  pello_tray.py        ikona płomienia, zasobnik, powiadomienia
  pello_schema.py      zakładka "Schemat instalacji"
  pello.ico            ikona pliku .exe
  build_exe.bat        buduje PelloMonitor.exe
  uruchom_program.bat  uruchamia program bez budowania .exe

WYMAGANIA
  Windows + Python 3.10 lub nowszy (python.org, przy instalacji zaznacz
  "Add Python to PATH"). Biblioteki pystray, pillow i keyring instalują się automatycznie.

JAK URUCHOMIĆ
  A) Bez budowania:  dwuklik na  uruchom_program.bat
  B) Plik .exe:      dwuklik na  build_exe.bat
                     gotowy program: dist\PelloMonitor.exe
                     (można go skopiować na dowolny komputer, Python już niepotrzebny)

PIERWSZE URUCHOMIENIE
  1. Zakładka "Ustawienia": wpisz adres IP sterownika (oraz login/hasło).
  2. Kliknij "Połącz" w prawym górnym rogu.
  3. Zakładki: Odczyty, Alarmy, Schemat instalacji, Sterowanie, Wykres, Parametry,
     Kopie, Ustawienia, Info.
  4. Zakładka "Parametry" pokazuje wszystkie wartości ze sterownika (wyszukiwarka,
     grupy, opisy po polsku) i pozwala zapisać zrzut do pliku CSV.

KOPIE ZAPASOWE USTAWIEŃ (zakładka "Kopie")
  Kopia to plik z WSZYSTKIMI parametrami odczytanymi ze sterownika (bez haseł i numeru
  seryjnego). Ten etap tylko czyta ze sterownika - niczego do niego nie wysyła.
  - Kopia "Pierwotna" powstaje automatycznie przy pierwszym połączeniu z danym sterownikiem
    i nigdy nie jest nadpisywana ani usuwana przez program (to stan z pierwszego połączenia
    programu, a nie ustawienia fabryczne). Wyjątkiem jest usunięcie pliku ręcznie z folderu.
  - "Zrób kopię teraz" zapisuje kopię z opisem (np. "przed zmianą krzywej").
  - "Porównaj": jedna kopia = porównanie ze stanem bieżącym sterownika, dwie kopie =
    porównanie ich ze sobą. Domyślnie widać tylko zmiany ustawień; odczyty na żywo
    (temperatury, stany, liczniki, czas) można włączyć przełącznikiem.
  - Pliki leżą w C:\Users\<Ty>\PelloMonitor\kopie. Przechowuj je na wypadek awarii dysku.

EDYCJA POJEDYNCZYCH PARAMETRÓW (zakładka "Parametry")
  Domyślnie program tylko czyta. Edycję odblokowujesz w Ustawieniach ("Edycja parametrów");
  po każdym uruchomieniu programu jest znów zablokowana.
  - Dwuklik w DOWOLNYM miejscu wiersza (albo Enter na zaznaczonym) otwiera okno zmiany
    wartości. Opis parametru zmienisz przyciskiem "Zmień opis..." albo prawym przyciskiem myszy.
    W polu nowej wartości separatorem dziesiętnym jest zawsze KROPKA (wpisany przecinek zamienia
    się na kropkę).
  - ZABLOKOWANE NA STAŁE (nie da się ich odblokować; zapis blokuje też warstwa komunikacji,
    więc nie działa też "Cofnij"): sieć (IP, maska, brama, DHCP, serwer zdalny), czas i data,
    tożsamość urządzenia, serwis (protokół, kody typu instalacji i kotła), spalanie (palnik,
    dmuchawa, podajnik, dawki paliwa, rozpalanie, wygaszanie), korekty czujników kotła, powrotu,
    spalin i podajnika oraz parametry bez opisu. Wyjątek: add_fuel (ilość ostatnio dosypanego
    paliwa) - zielony. Po najechaniu myszką na zablokowany wiersz pojawia się powód.
    Tylko do odczytu są też odczyty na żywo, harmonogramy, teksty i parametry RF / stref.
  - Kolory ryzyka (kolumna "Ryzyko"): zielone - nastawy temperatur; żółte - histerezy, czasy,
    korekty pozostałych czujników i inne nastawy regulacji; czerwone - czyszczenie i ustawienia
    urządzenia (drugie, dodatkowe potwierdzenie).
  - Przebieg: okno z nową wartością -> potwierdzenie "stara -> nowa" -> świeży odczyt
    (wartość nie mogła się zmienić) -> automatyczna kopia (rodzaj "Przed zmianą" w zakładce
    "Kopie"; bez kopii nic nie jest zapisywane) -> zapis -> potwierdzenie odczytem.
  - Dziennik zmian (pod tabelą parametrów, plik PelloMonitor\dziennik_zmian.json): czas,
    parametr, stara i nowa wartość, wynik i nazwa kopii. Przycisk "Cofnij zaznaczoną zmianę"
    przywraca starą wartość tym samym przebiegiem (potwierdzenia, kopia, odczyt, wpis).
    Cofnąć można tylko zmianę potwierdzoną odczytem i jeszcze niecofniętą.

ZMIANA NASTAW I POTWIERDZENIE ZAPISU
  Po wysłaniu nastawy program sprawdza odpowiedź sterownika (status rejestru) i dodatkowo
  odczytuje wartość z powrotem. Komunikat "potwierdzone przez sterownik" pojawia się tylko
  wtedy, gdy wartość naprawdę weszła w życie. Jeśli sterownik odmówi zapisu (np. brak
  uprawnień - access_denied) albo zignoruje nastawę, program pokaże ostrzeżenie, a pola
  nastaw wrócą do wartości ze sterownika. Do zmiany nastaw użytkownik musi mieć prawa zapisu.

HASŁO I BEZPIECZEŃSTWO
  Hasło zapisuje się tylko po zaznaczeniu "Zapamiętaj hasło". Kolejność metod:
    1. Menedżer poświadczeń Windows (biblioteka keyring),
    2. szyfrowanie Windows DPAPI - plik ustawień zawiera tylko zaszyfrowany ciąg, który
       odczyta wyłącznie to samo konto Windows na tym komputerze,
    3. jawny tekst w pliku ustawień - tylko ostateczność (np. system inny niż Windows);
       program wyraźnie ostrzega o tym w Ustawieniach.
  Hasło zapisane starszą wersją (jawnym tekstem) jest przenoszone automatycznie do
  bezpieczniejszej metody przy pierwszym uruchomieniu. Odznaczenie "Zapamiętaj hasło"
  usuwa zapamiętane hasło. Nie przenoś pliku ustawień na inny komputer - hasło trzeba
  tam wpisać ponownie.
  Odpowiedź sterownika zawiera też zakodowane dane logowania (parametry auth_*). Program
  ich nie wyświetla ani nie zapisuje (są odrzucane od razu po odczycie). Nie publikuj
  surowych zrzutów syncvalues.cgi w internecie.

PRACA W TLE
  Zamknięcie okna (X) chowa program do zasobnika przy zegarze.
  Start razem z Windows: skrót do PelloMonitor.exe --tray w folderze
  autostartu (Win+R -> shell:startup).

GDZIE SĄ DANE
  Ustawienia:  C:\Users\<Ty>\.pello_monitor.json   (bez hasła, jeśli działa szyfrowanie)
  Historia:    C:\Users\<Ty>\PelloMonitor\pello_RRRR-MM-DD.csv
  Kopie:       C:\Users\<Ty>\PelloMonitor\kopie\
  Dziennik:    C:\Users\<Ty>\PelloMonitor\dziennik_zmian.json

WARUNKI (wersja FREE)
  Program darmowy do użytku prywatnego i niekomercyjnego. Zakaz sprzedaży oraz
  usuwania informacji o autorze. Udostępniany "tak jak jest", bez gwarancji -
  nastawy sterownika zmieniasz na własną odpowiedzialność. Program nie jest
  oficjalnym produktem esterownik.pl.
  (c) 2026 Mariusz
