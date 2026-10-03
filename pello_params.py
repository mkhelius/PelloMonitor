"""
pello_params.py - katalog parametrów sterownika Pello (opisy, jednostki, grupy, formatowanie).
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>

Sterownik Pello D zwraca ponad 800 parametrów. Tu opisano te, których znaczenie jest pewne
(nazwy wynikają z nazw kluczy i z wartości w zrzucie ze sterownika). Pozostałe trafiają do grup
„… (bez opisu)” - wciąż widać je w zakładce „Parametry”, a opis możesz nadać sam (dwuklik na
wierszu); własne opisy zapisują się w pliku  ~/.pello_opisy.json  (można go też edytować ręcznie).

Rodzaje wartości:  "num" liczba | "onoff" Wł./Wył. | "yesno" Tak/Nie | "unix" data i godzina |
                   "dur" czas trwania w sekundach | "text" tekst
"""
import datetime
import json
import re
from pathlib import Path

OVERRIDES_FILE = Path.home() / ".pello_opisy.json"

# klucze, których NIE pokazujemy ani nie zapisujemy (dane dostępowe do sterownika)
SENSITIVE_PREFIXES = ("auth_",)

# ---------------------------------------------------------------- katalog (grupa -> parametry)
# (klucz, opis, jednostka, rodzaj)
_SRC = [
    ("Temperatury", [
        ("tkot_value", "Temperatura kotła", "°C", "num"),
        ("tpow_value", "Temperatura powrotu", "°C", "num"),
        ("tcwu_value", "Temperatura CWU", "°C", "num"),
        ("tsp_value", "Temperatura spalin", "°C", "num"),
        ("tzew_value", "Temperatura zewnętrzna", "°C", "num"),
        ("tzew_act", "Temperatura zewnętrzna (używana w regulacji)", "°C", "num"),
        ("t1_value", "Temperatura obiegu CO 1 (czujnik T1)", "°C", "num"),
        ("t2_value", "Temperatura obiegu CO 2 (czujnik T2)", "°C", "num"),
        ("tpod_value", "Temperatura podajnika", "°C", "num"),
        ("twew_value", "Temperatura pokojowa CO 1 (czujnik wewn.)", "°C", "num"),
        ("tkot_cal", "Korekta czujnika kotła", "°C", "num"),
        ("tpow_cal", "Korekta czujnika powrotu", "°C", "num"),
        ("tcwu_cal", "Korekta czujnika CWU", "°C", "num"),
        ("tsp_cal", "Korekta czujnika spalin", "°C", "num"),
        ("tzew_cal", "Korekta czujnika zewnętrznego", "°C", "num"),
        ("t1_cal", "Korekta czujnika T1", "°C", "num"),
        ("t2_cal", "Korekta czujnika T2", "°C", "num"),
        ("tpod_cal", "Korekta czujnika podajnika", "°C", "num"),
        ("twew_cal", "Korekta czujnika pokojowego", "°C", "num"),
        ("tzew_sensor", "Czujnik zewnętrzny (typ)", "", "num"),
    ]),
    ("Wyjścia (stan urządzeń)", [
        ("out_pomp1", "Pompa CO 1", "", "onoff"),
        ("out_pomp2", "Pompa CO 2", "", "onoff"),
        ("out_cwu", "Pompa CWU", "", "onoff"),
        ("out_miesz", "Mieszadło", "", "onoff"),
        ("out_pod", "Podajnik", "", "onoff"),
        ("out_dm", "Dmuchawa", "", "onoff"),
        ("out_zaw4d", "Zawór 4D", "", "num"),
        ("out_aux", "Wyjście dodatkowe (AUX)", "", "onoff"),
        ("out_tank", "Wyjście zbiornika buforowego", "", "onoff"),
        ("out_clean_wym", "Czyszczenie wymiennika (wyjście)", "", "onoff"),
        ("_pompa_kotla", "Pompa kotła (pochodna: pracuje któraś pompa)", "", "onoff"),
    ]),
    ("Wejścia cyfrowe", [
        ("di_zawl", "Wejście ZAWL", "", "onoff"),
        ("di_zas", "Wejście ZAS", "", "onoff"),
        ("di_alarm", "Wejście alarmu zewnętrznego", "", "onoff"),
        ("di_termik", "Wejście TERMIK", "", "onoff"),
        ("di_stb", "Wejście STB", "", "onoff"),
        ("di_term1", "Wejście termostatu 1", "", "onoff"),
        ("di_term2", "Wejście termostatu 2", "", "onoff"),
    ]),
    ("Alarmy – czujniki", [
        ("alarm_tkot", "Awaria czujnika kotła", "", "onoff"),
        ("alarm_tpow", "Awaria czujnika powrotu", "", "onoff"),
        ("alarm_tpod", "Awaria czujnika podajnika", "", "onoff"),
        ("alarm_tcwu", "Awaria czujnika CWU", "", "onoff"),
        ("alarm_twew", "Awaria czujnika pokojowego", "", "onoff"),
        ("alarm_tzew", "Awaria czujnika zewnętrznego", "", "onoff"),
        ("alarm_t1", "Awaria czujnika T1", "", "onoff"),
        ("alarm_t2", "Awaria czujnika T2", "", "onoff"),
        ("alarm_tsp", "Awaria czujnika spalin", "", "onoff"),
    ]),
    ("Alarmy", [
        ("alarm_rozp", "Alarm rozpalania", "", "onoff"),
        ("alarm_rozp_ext", "Alarm rozpalania (rozszerzony)", "", "onoff"),
        ("alarm_pod_zaplon", "Alarm: zapłon w podajniku", "", "onoff"),
        ("alarm_tkot_90", "Alarm: zbyt wysoka temp. kotła", "", "onoff"),
        ("alarm_tpod_hi", "Alarm: zbyt wysoka temp. podajnika", "", "onoff"),
        ("alarm_tco1_hi", "Alarm: zbyt wysoka temp. CO 1", "", "onoff"),
        ("alarm_termik", "Alarm STB (termik)", "", "onoff"),
        ("alarm_stb", "Alarm STB", "", "onoff"),
        ("alarm_zew", "Alarm zewnętrzny", "", "onoff"),
        ("alarm_zasobnik", "Alarm zasobnika", "", "onoff"),
        ("alarm_otw_zasob", "Alarm: otwarty zasobnik", "", "onoff"),
        ("alarm_poz_ruszt", "Alarm: pozycja rusztu", "", "onoff"),
        ("alarm_cis", "Alarm ciśnienia", "", "onoff"),
        ("alarm_clean_exch", "Alarm: czas na czyszczenie wymiennika", "", "onoff"),
        ("alarm_clwym", "Alarm czyszczenia wymiennika", "", "onoff"),
        ("alarm_ipconflict", "Alarm: konflikt adresu IP", "", "onoff"),
        ("alarm_tank_hi", "Alarm zbiornika: czujnik górny", "", "onoff"),
        ("alarm_tank_lo", "Alarm zbiornika: czujnik dolny", "", "onoff"),
        ("alarm_tank_hitemp", "Alarm zbiornika: zbyt wysoka temp.", "", "onoff"),
        ("dp_alarm", "Alarm DP", "", "onoff"),
        ("mpl_alarm", "Alarm modułu palnika", "", "onoff"),
    ]),
    ("Palnik i paliwo", [
        ("pl_status", "Status palnika", "", "num"),
        ("pl_status_ext", "Status palnika – kod rozszerzony", "", "num"),
        ("kot_status", "Status kotła (kod)", "", "num"),
        ("pl_power_kw", "Moc palnika", "kW", "num"),
        ("pl_power", "Moc palnika", "%", "num"),
        ("pl_flame", "Płomień", "%", "num"),
        ("pl_fuel_flow", "Spalanie paliwa", "kg/h", "num"),
        ("fuel_level", "Poziom paliwa", "%", "num"),
        ("fuel_level_enum", "Poziom paliwa (stopień)", "", "num"),
        ("time_to_empty", "Czas do braku paliwa", "h", "num"),
        ("next_fuel_time", "Data następnego zasypu", "", "unix"),
        ("add_fuel", "Ilość ostatnio dosypanego paliwa", "kg", "num"),
        ("add_fuel_time", "Czas ostatniego zasypu", "", "unix"),
        ("pl_kot_pmax", "Maksymalna moc kotła", "kW", "num"),
        ("pl_fuel_calor", "Wartość opałowa paliwa", "MJ/kg", "num"),
        ("pl_calib_en", "Kalibracja palnika włączona", "", "yesno"),
        ("pl_calib_time", "Czas kalibracji", "s", "num"),
        ("pl_calib_perf", "Wartość kalibracji", "g", "num"),
        ("pl_min_time", "Minimalny czas pracy palnika", "s", "num"),
        ("pl_tptotal", "Łączny czas pracy palnika", "", "dur"),
        ("pl_plimit", "Limit mocy palnika", "%", "num"),
        ("wsp_moc", "Współczynnik mocy", "%", "num"),
        ("pl_dm_max", "Maks. prędkość dmuchawy", "%", "num"),
        ("pl_dm_min", "Min. prędkość dmuchawy", "%", "num"),
        ("pl_roz_dm", "Rozpalanie: dmuchawa", "%", "num"),
        ("pl_roz_dm2", "Rozpalanie: dmuchawa 2", "%", "num"),
        ("pl_wyg_dm", "Wygaszanie: dmuchawa", "%", "num"),
        ("pl_stab_dm", "Stabilizacja: dmuchawa", "%", "num"),
        ("pl_wyg_tsp", "Wygaszanie: temp. spalin", "°C", "num"),
        ("pl_ruszt_en", "Ruszt włączony", "", "yesno"),
        ("pl_opto_en", "Optoczujnik włączony", "", "yesno"),
    ]),
    ("Moduł palnika i dmuchawa", [
        ("act_dm_speed", "Prędkość dmuchawy", "%", "num"),
        ("dm_set_rpm", "Zadane obroty dmuchawy", "obr/min", "num"),
        ("mpl_dm_rpm", "Obroty dmuchawy", "obr/min", "num"),
        ("mpl_dm_max", "Maks. obroty dmuchawy", "obr/min", "num"),
        ("dm_man", "Dmuchawa – nastawa ręczna", "%", "num"),
        ("mpl_temp", "Temperatura modułu palnika", "°C", "num"),
        ("mpl_opto", "Optoczujnik – wartość", "", "num"),
        ("mpl_feed", "Moduł palnika: podawanie", "", "onoff"),
        ("mpl_heat", "Moduł palnika: grzałka", "", "onoff"),
        ("mpl_clean", "Moduł palnika: czyszczenie", "", "onoff"),
        ("mpl_hall_en", "Czujnik Halla włączony", "", "yesno"),
        ("exh_en", "Wentylator wyciągowy włączony", "", "yesno"),
        ("exh_fan_speed", "Prędkość wentylatora wyciągowego", "%", "num"),
        ("exh_tmax", "Wentylator wyciągowy: maks. temp. spalin", "°C", "num"),
        ("exh_plim", "Wentylator wyciągowy: limit mocy", "%", "num"),
    ]),
    ("Podajnik", [
        ("pod_run_time", "Czas pracy podajnika", "", "dur"),
        ("pod_run_time_str", "Czas pracy podajnika (tekst)", "", "text"),
        ("pod_run_time_last", "Czas pracy podajnika – ostatni cykl", "", "dur"),
        ("pod_tmax", "Maks. temperatura podajnika", "°C", "num"),
        ("pod_man_runtime", "Podajnik – czas pracy ręcznej", "s", "num"),
    ]),
    ("Czyszczenie", [
        ("clean_act_kg", "Paliwo spalone od czyszczenia", "kg", "num"),
        ("clean_exch_kg", "Limit paliwa do czyszczenia wymiennika", "kg", "num"),
        ("clean_burn_time", "Czas palenia od czyszczenia", "", "dur"),
    ]),
    ("Tryb pracy (Zima/Lato)", [
        ("zima_lato", "Tryb pracy (Zima/Lato)", "", "num"),
        ("zima_lato_state", "Stan trybu Zima/Lato", "", "num"),
        ("tryb_auto_state", "Tryb pieca", "", "num"),
        ("autolato_tzew", "Auto-lato: temperatura zewnętrzna", "°C", "num"),
        ("autolato_hist", "Auto-lato: histereza", "°C", "num"),
        ("pog_en", "Pogodówka kotła włączona", "", "yesno"),
        ("pog_krzyw1", "Krzywa pogodowa kotła – punkt 1", "°C", "num"),
        ("pog_krzyw2", "Krzywa pogodowa kotła – punkt 2", "°C", "num"),
        ("power_state", "Stan zasilania sterownika", "", "num"),
    ]),
    ("Nastawy kotła", [
        ("kot_tzad", "Zadana temperatura kotła", "°C", "num"),
        ("kot_tact", "Aktualna zadana temperatura kotła", "°C", "num"),
        ("kot_tobn", "Obniżenie temperatury kotła", "°C", "num"),
        ("kot_tmin", "Minimalna temperatura kotła", "°C", "num"),
        ("kot_st_tobn", "Obniżenie kotła aktywne", "", "yesno"),
        ("kot_hist", "Histereza kotła", "", "num"),
        ("kot_hist2", "Histereza kotła 2", "", "num"),
        ("tpow_min", "Minimalna temperatura powrotu", "°C", "num"),
        ("ochr_pow", "Ochrona powrotu (tryb)", "", "num"),
        ("pid_k", "Regulator PID: wzmocnienie (K)", "", "num"),
        ("pid_ti", "Regulator PID: czas całkowania (Ti)", "", "num"),
        ("pid_td", "Regulator PID: czas różniczkowania (Td)", "", "num"),
        ("pid_factor", "Regulator PID: współczynnik", "", "num"),
    ]),
    ("CWU i cyrkulacja", [
        ("fun_cwu", "Funkcja CWU włączona", "", "yesno"),
        ("cwu_tzad", "Zadana temperatura CWU", "°C", "num"),
        ("cwu_tact", "Aktualna zadana temperatura CWU", "°C", "num"),
        ("cwu_tobn", "Obniżenie temperatury CWU", "°C", "num"),
        ("cwu_st_tobn", "Obniżenie CWU aktywne", "", "yesno"),
        ("cwu_out_state", "Stan pompy CWU", "", "onoff"),
        ("cwu_state", "Stan CWU (kod)", "", "num"),
        ("cwu_podb_kot", "CWU: podbicie kotła", "", "num"),
        ("cwu_hist1", "Histereza CWU 1", "", "num"),
        ("cwu_hist2", "Histereza CWU 2", "", "num"),
    ]),
    ("Pompy i zawór 4D", [
        ("pomp_ton", "Pompa: temperatura załączenia", "°C", "num"),
        ("pomp_co_ton", "Pompa CO: temperatura załączenia", "°C", "num"),
        ("hist_pump", "Pompa: histereza", "°C", "num"),
        ("hist_pump_co", "Pompa CO: histereza", "°C", "num"),
        ("hist_miesz", "Mieszadło: histereza", "°C", "num"),
        ("pomp_ext_func", "Funkcja pompy zewnętrznej", "", "num"),
        ("zaw4d_open_time", "Zawór 4D: czas pełnego otwarcia", "s", "num"),
        ("zaw4d_hist", "Zawór 4D: histereza", "°C", "num"),
        ("zaw4d_p", "Zawór 4D: regulator P", "", "num"),
        ("zaw4d_i", "Zawór 4D: regulator I", "", "num"),
        ("zaw4d_dir", "Zawór 4D: kierunek", "", "num"),
    ]),
    ("Zbiornik buforowy", [
        ("tank_en", "Zbiornik buforowy włączony", "", "yesno"),
        ("temp_tank_hi", "Temperatura zbiornika – góra", "°C", "num"),
        ("temp_tank_lo", "Temperatura zbiornika – dół", "°C", "num"),
        ("tank_tzad", "Zbiornik: zadana temperatura", "°C", "num"),
        ("tank_hi_cal", "Korekta czujnika zbiornika – góra", "°C", "num"),
        ("tank_lo_cal", "Korekta czujnika zbiornika – dół", "°C", "num"),
    ]),
    ("Urządzenie i sieć", [
        ("device_name", "Nazwa urządzenia", "", "text"),
        ("device_type", "Typ urządzenia", "", "text"),
        ("device_sn", "Numer seryjny", "", "text"),
        ("device_id", "Identyfikator urządzenia", "", "text"),
        ("device_location", "Lokalizacja", "", "text"),
        ("device_soft_version", "Wersja oprogramowania", "", "text"),
        ("device_hard_version", "Wersja sprzętu", "", "text"),
        ("prod_date", "Data produkcji", "", "unix"),
        ("datetime", "Czas sterownika", "", "unix"),
        ("localtimezone", "Strefa czasowa", "", "text"),
        ("rtc_calib_en", "Kalibracja zegara RTC", "", "yesno"),
        ("rtc_correction", "Korekta zegara RTC", "", "num"),
        ("accesslevel", "Poziom dostępu", "", "num"),
        ("eth_mac", "Adres MAC", "", "text"),
        ("eth_ip", "Adres IP", "", "text"),
        ("eth_mask", "Maska sieci", "", "text"),
        ("eth_gate", "Brama domyślna", "", "text"),
        ("eth_dhcp", "DHCP", "", "yesno"),
        ("eth_ip_ro", "Adres IP (aktualny)", "", "text"),
        ("eth_mask_ro", "Maska sieci (aktualna)", "", "text"),
        ("eth_gate_ro", "Brama (aktualna)", "", "text"),
        ("remote_server_status", "Status serwera zdalnego", "", "num"),
        ("rf_module", "Moduł RF", "", "yesno"),
        ("en_scr", "Ekran włączony", "", "yesno"),
        ("en_serv", "Tryb serwisowy", "", "yesno"),
        ("silent", "Tryb cichy", "", "yesno"),
        ("upd_fr_name", "Plik aktualizacji", "", "text"),
    ]),
]

# ---------------------------------------------------------------- opisy uzupełniające
# Skróty rozwinięte wprost z nazw kluczy (bez zgadywania jednostek). Jeśli któryś opis Ci nie pasuje -
# zmień go w programie: zakładka „Parametry” -> dwuklik na wierszu.
_MORE = {
    "Urządzenie i sieć": [
        ("daytime", "Czas doby (kod wewnętrzny)", "", "num"),
        ("date", "Data (kod wewnętrzny)", "", "num"),
        ("time", "Czas (kod wewnętrzny)", "", "num"),
        ("eth_iface", "Interfejs sieciowy", "", "num"),
        ("pattern_lang", "Język (maska)", "", "num"),
        ("rf_update", "Moduł RF: aktualizacja", "", "num"),
        ("rf_offset", "Moduł RF: przesunięcie", "", "num"),
        ("rf_status", "Moduł RF: status", "", "num"),
        ("node_add", "RF: dodawanie urządzenia", "", "num"),
        ("node_del", "RF: usuwanie urządzenia", "", "num"),
        ("node_st", "RF: stan", "", "num"),
        ("node_time", "RF: czas", "", "num"),
        ("log", "Logowanie zdarzeń", "", "num"),
        ("screen_code", "Kod ekranu", "", "num"),
        ("lcd_hdr", "Nagłówek wyświetlacza", "", "num"),
        ("en_ext_out", "Wyjścia zewnętrzne włączone", "", "yesno"),
        ("upd_pgs", "Aktualizacja: postęp", "", "num"),
        ("install_type", "Typ instalacji (kod)", "", "num"),
        ("typ_kotla", "Typ kotła (kod)", "", "num"),
        ("burner", "Palnik", "", "text"),
        ("prot_serv", "Protokół serwisowy", "", "num"),
        ("mod1", "Moduł 1", "", "num"),
        ("mod2", "Moduł 2 (licznik)", "", "num"),
        ("mod2_imp_l", "Moduł 2: impulsy na litr", "", "num"),
        ("mod2_flow", "Moduł 2: przepływ", "", "num"),
        ("mod2_power", "Moduł 2: moc", "", "num"),
        ("mod2_energy", "Moduł 2: energia", "", "num"),
        ("wh_global", "Licznik energii: łącznie", "", "num"),
        ("wh_yr", "Licznik energii: rok", "", "num"),
        ("wh_mon", "Licznik energii: miesiąc", "", "num"),
        ("trv_mode", "Głowice TRV: tryb", "", "num"),
        ("trv_calib_day", "Głowice TRV: dzień kalibracji", "", "num"),
        ("trv_calib_hour", "Głowice TRV: godzina kalibracji", "", "num"),
        ("wnd_time", "Wykrywanie okna: czas", "", "num"),
        ("wnd_hist", "Wykrywanie okna: histereza", "", "num"),
        ("wnd_cfg", "Wykrywanie okna: konfiguracja", "", "num"),
        ("limit_power", "Ograniczenie mocy", "", "num"),
    ],
    "Wejścia cyfrowe": [
        ("di_alarm_time", "Wejście alarmowe: czas", "", "num"),
        ("di_alarm_inv", "Wejście alarmowe: odwrócone", "", "yesno"),
        ("di_alarm_stop", "Wejście alarmowe: zatrzymuje kocioł", "", "yesno"),
        ("di_zas_en", "Wejście zasobnika włączone", "", "yesno"),
        ("di_zas_delay", "Wejście zasobnika: opóźnienie", "", "num"),
    ],
    "Palnik i paliwo": [
        ("et_stop", "Aktualny etap: stop", "", "yesno"),
        ("et_roz", "Aktualny etap: rozpalanie", "", "yesno"),
        ("et_pr", "Aktualny etap: praca", "", "yesno"),
        ("et_wyg", "Aktualny etap: wygaszanie", "", "yesno"),
        ("pl_flame_b", "Płomień (czujnik B)", "", "num"),
        ("pl_tfire", "Czas palenia (licznik)", "", "num"),
        ("pl_hfire", "Godziny palenia (licznik)", "", "num"),
        ("pl_clean", "Czyszczenie palnika aktywne", "", "yesno"),
        ("pl_clean_toff", "Czyszczenie: przerwa", "", "num"),
        ("pl_roz_fire", "Rozpalanie: płomień", "", "num"),
        ("pl_roz_fuel", "Rozpalanie: paliwo", "", "num"),
        ("pl_roz_stab", "Rozpalanie: stabilizacja", "", "num"),
        ("pl_roz_tmax", "Rozpalanie: czas maksymalny", "", "num"),
        ("pl_roz_theat", "Rozpalanie: czas grzania", "", "num"),
        ("pl_roz_tsp", "Rozpalanie: temperatura spalin", "", "num"),
        ("pl_wyg_tmin", "Wygaszanie: czas minimalny", "", "num"),
        ("pl_wyg_tmax", "Wygaszanie: czas maksymalny", "", "num"),
        ("pl_wyg_fire", "Wygaszanie: płomień", "", "num"),
        ("pl_wyg_tclean", "Wygaszanie: czyszczenie", "", "num"),
        ("pl_wyg_state", "Wygaszanie: stan", "", "num"),
        ("pl_wyg_cnt", "Wygaszanie: licznik", "", "num"),
        ("pl_fuel_period", "Podawanie paliwa: okres", "", "num"),
        ("pl_fuel_max", "Dawka paliwa: maksymalna", "", "num"),
        ("pl_fuel_min", "Dawka paliwa: minimalna", "", "num"),
        ("pl_stab_fuel", "Stabilizacja: paliwo", "", "num"),
        ("pl_cykl_pmax", "Moc cyklu: maksymalna", "", "num"),
        ("pl_plimit_state", "Ograniczenie mocy: stan", "", "num"),
        ("pl_dmk_min", "Dmuchawa kotła: minimum", "", "num"),
        ("pl_dmk_max", "Dmuchawa kotła: maksimum", "", "num"),
        ("tr_gr_tsp", "Próg temperatury spalin", "", "num"),
        ("proc_time", "Czas procesu", "", "num"),
        ("proc_stop", "Zatrzymanie procesu", "", "yesno"),
        ("fire_time", "Czas palenia", "", "num"),
        ("dop_dm_up", "Dopalanie: zwiększenie dmuchawy", "", "yesno"),
        ("dop_wait", "Dopalanie: oczekiwanie", "", "num"),
        ("stats_pwr", "Statystyka mocy", "", "num"),
        ("fuel_fill", "Zasyp paliwa (kod)", "", "num"),
    ],
    "Moduł palnika i dmuchawa": [
        ("mpl_di_hall2", "Czujnik Halla 2 (wejście)", "", "onoff"),
        ("exh_fan_mode", "Wentylator wyciągowy: tryb", "", "num"),
        ("dp_value", "Ciśnienie różnicowe (dp)", "", "num"),
        ("dp_en", "Czujnik ciśnienia różnicowego włączony", "", "yesno"),
        ("rp_min_cis", "Regulacja podciśnienia: ciśnienie min.", "", "num"),
        ("rp_min_obr", "Regulacja podciśnienia: obroty min.", "", "num"),
        ("rp_min_hist", "Regulacja podciśnienia: histereza min.", "", "num"),
        ("rp_max_cis", "Regulacja podciśnienia: ciśnienie maks.", "", "num"),
        ("rp_max_obr", "Regulacja podciśnienia: obroty maks.", "", "num"),
        ("rp_max_hist", "Regulacja podciśnienia: histereza maks.", "", "num"),
        ("rp_kor_obr", "Regulacja podciśnienia: korekta obrotów", "", "num"),
        ("rp_delay", "Regulacja podciśnienia: opóźnienie", "", "num"),
        ("rp_active", "Regulacja podciśnienia aktywna", "", "yesno"),
        ("od_cis", "Odciąg: ciśnienie", "", "num"),
        ("od_delay", "Odciąg: opóźnienie", "", "num"),
        ("od_pmin", "Odciąg: moc minimalna", "", "num"),
        ("przedm_en", "Przedmuch włączony", "", "yesno"),
        ("przedm_toff", "Przedmuch: czas przerwy", "", "num"),
        ("przedm_ton", "Przedmuch: czas pracy", "", "num"),
        ("przedm_dm", "Przedmuch: dmuchawa", "", "num"),
    ],
    "Podajnik": [
        ("pod_typ", "Typ podajnika (kod)", "", "num"),
        ("pod_ton", "Podajnik: czas pracy", "", "num"),
        ("pod_toff", "Podajnik: czas przerwy", "", "num"),
        ("pod_run_time_hour", "Podajnik: czas pracy (licznik)", "", "num"),
    ],
    "Czyszczenie": [
        ("clean_hsleep", "Czyszczenie: uśpienie – od godziny", "", "num"),
        ("clean_tsleep", "Czyszczenie: uśpienie – czas", "", "num"),
        ("clean_hall_en", "Czyszczenie: czujnik Halla", "", "yesno"),
        ("clwym_en", "Czyszczenie wymiennika włączone", "", "yesno"),
        ("clwym_toff", "Czyszczenie wymiennika: przerwa", "", "num"),
        ("clwym_ton", "Czyszczenie wymiennika: praca", "", "num"),
        ("clwym_err", "Czyszczenie wymiennika: błąd", "", "num"),
        ("clwym_time", "Czyszczenie wymiennika: czas", "", "num"),
        ("clsln_en", "Czyszczenie (clsln) włączone", "", "yesno"),
        ("clsln_ton", "Czyszczenie (clsln): czas pracy", "", "num"),
        ("clsln_toff", "Czyszczenie (clsln): czas przerwy", "", "num"),
        ("clsln_dm", "Czyszczenie (clsln): dmuchawa", "", "num"),
    ],
    "CWU i cyrkulacja": [
        ("cyrk_pomp_on", "Cyrkulacja: czas pracy", "", "num"),
        ("cyrk_pomp_off", "Cyrkulacja: czas przerwy", "", "num"),
        ("cyrk_pomp_ton", "Cyrkulacja: próg temperatury", "", "num"),
    ],
    "Zbiornik buforowy": [
        ("tank_hist", "Zbiornik: histereza", "", "num"),
    ],
}
for _g, _extra in _MORE.items():
    for _i, (_name, _rows) in enumerate(_SRC):
        if _name == _g:
            _rows.extend(r for r in _extra if r[0] not in {x[0] for x in _rows})
            break
    else:
        _SRC.append((_g, list(_extra)))


# parametry obiegów ob1..ob6:  sufiks -> (opis, jednostka, rodzaj)
OB_FIELDS = {
    "typ": ("Typ obiegu (kod)", "", "num"),
    "tzad": ("Zadana temperatura obiegu", "°C", "num"),
    "tobn": ("Obniżenie temperatury obiegu", "°C", "num"),
    "tmax": ("Maksymalna temperatura obiegu", "°C", "num"),
    "pomp_on": ("Pompa: temperatura włączenia", "°C", "num"),
    "pomp_off": ("Pompa: temperatura wyłączenia", "°C", "num"),
    "pok_lo": ("Temp. pokojowa obniżona", "°C", "num"),
    "pok_norm": ("Temp. pokojowa normalna", "°C", "num"),
    "pok_hi": ("Temp. pokojowa podwyższona", "°C", "num"),
    "pok_hist": ("Histereza temp. pokojowej", "°C", "num"),
    "pok_tact": ("Temp. pokojowa aktualna", "°C", "num"),
    "pok_tzad": ("Temp. pokojowa zadana", "°C", "num"),
    "pok_heat": ("Grzanie wg termostatu pokojowego", "", "yesno"),
    "pump_pok": ("Pompa wg termostatu pokojowego", "", "yesno"),
    "pog_en": ("Pogodówka obiegu włączona", "", "yesno"),
    "pog_krzyw1": ("Krzywa pogodowa – punkt 1", "°C", "num"),
    "pog_krzyw2": ("Krzywa pogodowa – punkt 2", "°C", "num"),
    "zaw4d_tzad": ("Zawór: zadana temperatura", "°C", "num"),
    "zaw4d_pos": ("Zawór: pozycja", "%", "num"),
    "zaw4d_max": ("Zawór: maks. otwarcie", "%", "num"),
    "zaw4d_min": ("Zawór: min. otwarcie", "%", "num"),
    "zaw4d_open_time": ("Zawór: czas pełnego otwarcia", "s", "num"),
    "prog": ("Harmonogram", "", "text"),
    "zaw4d_prog": ("Harmonogram zaworu", "", "text"),
    "out_pump": ("Wyjście pompy", "", "onoff"),
    "t1_alarm": ("Alarm czujnika T1", "", "onoff"),
    "t2_alarm": ("Alarm czujnika T2", "", "onoff"),
    "hitemp_alarm": ("Alarm: zbyt wysoka temperatura", "", "onoff"),
    "mr3_alarm": ("Alarm modułu MR3", "", "onoff"),
    "di_term": ("Wejście termostatu", "", "onoff"),
    "t1": ("Temperatura T1", "°C", "num"),
    "t2": ("Temperatura T2", "°C", "num"),
    "t1_cal": ("Korekta czujnika T1", "°C", "num"),
    "t2_cal": ("Korekta czujnika T2", "°C", "num"),
    "pok_pre": ("Wyprzedzenie regulacji pokojowej", "", "num"),
    "pok_typ": ("Typ regulacji pokojowej (kod)", "", "num"),
    "term_delay": ("Termostat: opóźnienie", "", "num"),
    "term_state": ("Termostat: stan", "", "num"),
    "zaw4d_hist": ("Zawór: histereza", "", "num"),
    "zaw4d_p": ("Zawór: człon P regulatora", "", "num"),
    "zaw4d_i": ("Zawór: człon I regulatora", "", "num"),
    "zaw4d_dir": ("Zawór: kierunek", "", "num"),
    "zaw4d_sta": ("Zawór: stan (kod)", "", "num"),
    "out_zaw4d": ("Wyjście zaworu", "", "num"),
    "pl_wyg": ("Wygaszanie palnika wg obiegu", "", "yesno"),
}

# urządzenia RF (linie 1..99 odpowiedzi):  sufiks -> (opis, jednostka, rodzaj)
RF_FIELDS = {
    "t": ("Typ urządzenia", "", "text"),
    "v": ("Wersja", "", "text"),
    "temp": ("Temperatura", "°C", "num"),
    "rh": ("Wilgotność", "%", "num"),
    "bat": ("Bateria", "%", "num"),
    "sig": ("Sygnał radiowy", "%", "num"),
    "alarm": ("Alarm", "", "onoff"),
}

# strefy termostatów (linie 100+ odpowiedzi)
ZONE_FIELDS = {
    "t_lo": ("Temp. obniżona", "°C", "num"),
    "t_norm": ("Temp. normalna", "°C", "num"),
    "t_hi": ("Temp. podwyższona", "°C", "num"),
    "temp": ("Temperatura", "°C", "num"),
    "heat": ("Grzanie", "", "yesno"),
    "name": ("Nazwa", "", "text"),
    "tbl": ("Harmonogram", "", "text"),
    "alarm": ("Alarm", "", "onoff"),
    "temp_pre": ("Wyprzedzenie", "", "num"),
    "lock": ("Blokada", "", "yesno"),
    "relays": ("Przekaźniki (maska)", "", "num"),
    "hb0": ("Łączność hb0", "", "num"),
    "hb1": ("Łączność hb1", "", "num"),
    "p1": ("Parametr p1", "", "num"),
    "enable": ("Aktywne (maska)", "", "num"),
    "obx": ("Numer obwodu (obx)", "", "num"),
}

# kolejność grup w tabeli
GROUP_ORDER = [g for g, _ in _SRC]
for _n in range(1, 7):
    GROUP_ORDER.append(f"Obwód {_n}")
GROUP_ORDER += ["Urządzenia RF", "Strefy termostatów", "Harmonogramy",
                "Palnik (bez opisu)", "Moduł palnika (bez opisu)", "Czyszczenie (bez opisu)",
                "Pozostałe parametry (bez opisu)"]

CATALOG = {}
for _group, _rows in _SRC:
    for _key, _desc, _unit, _kind in _rows:
        CATALOG[_key] = (_desc, _unit, _kind, _group)

_PREFIX_GROUPS = (
    ("mpl_", "Moduł palnika (bez opisu)"), ("pl_", "Palnik (bez opisu)"),
    ("clean_", "Czyszczenie (bez opisu)"), ("clwym_", "Czyszczenie (bez opisu)"),
    ("clsln_", "Czyszczenie (bez opisu)"),
)
_PROG_RE = re.compile(r"(^|_)(prog|tbl)$")
_OB_RE = re.compile(r"^ob(\d+)_(.+)$")
_RF_RE = re.compile(r"^rf(\d+)_(.+)$")
_ZONE_RE = re.compile(r"^strefa(\d+)_(.+)$")

# nazwane wartości (wyliczenia)
_ON_OFF = {"0": "Wył.", "1": "Wł."}
ENUMS = {
    "pl_status": {"0": "Stop", "1": "Rozpalanie", "2": "Praca", "3": "Wygaszanie", "4": "Czyszczenie"},
    "tryb_auto_state": {"0": "Ręczny", "1": "Automatyczny", "2": "Alarmowy"},
    "out_zaw4d": {"0": "Wyłączony", "1": "Otwierany", "2": "Zamykany"},
    "zima_lato": {"0": "Zima", "1": "Lato"},
}

# ---------------------------------------------------------------- własne opisy użytkownika
_overrides = {}


def load_overrides():
    global _overrides
    try:
        data = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
        _overrides = {str(k): str(v) for k, v in data.items() if str(v).strip()}
    except Exception:
        _overrides = {}


def set_override(key, text):
    """Zapisuje własny opis parametru (pusty tekst = przywrócenie opisu domyślnego)."""
    text = (text or "").strip()
    if text:
        _overrides[key] = text
    else:
        _overrides.pop(key, None)
    try:
        OVERRIDES_FILE.write_text(json.dumps(_overrides, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


load_overrides()


# ---------------------------------------------------------------- informacje o parametrze
def info(key):
    """Zwraca (opis, jednostka, rodzaj, grupa). Opis pusty = parametr bez opisu."""
    if key in CATALOG:
        return CATALOG[key]
    m = _OB_RE.match(key)
    if m:
        n, suffix = m.group(1), m.group(2)
        grp = f"Obwód {n}"
        if suffix in OB_FIELDS:
            desc, unit, kind = OB_FIELDS[suffix]
            if suffix in ("prog", "zaw4d_prog"):
                return (desc, unit, kind, "Harmonogramy")
            return (desc, unit, kind, grp)
        return ("", "", "num", grp)
    m = _RF_RE.match(key)
    if m:
        n, suffix = m.group(1), m.group(2)
        desc, unit, kind = RF_FIELDS.get(suffix, ("", "", "num"))
        return (f"RF {n}: {desc}" if desc else "", unit, kind, "Urządzenia RF")
    m = _ZONE_RE.match(key)
    if m:
        n, suffix = m.group(1), m.group(2)
        desc, unit, kind = ZONE_FIELDS.get(suffix, ("", "", "num"))
        kind = "text" if suffix in ("tbl", "name") else kind
        return (f"Strefa {n}: {desc}" if desc else "", unit, kind, "Strefy termostatów")
    if _PROG_RE.search(key):
        return ("Harmonogram", "", "text", "Harmonogramy")
    for prefix, grp in _PREFIX_GROUPS:
        if key.startswith(prefix):
            return ("", "", "num", grp)
    return ("", "", "num", "Pozostałe parametry (bez opisu)")


def describe(key):
    """Opis do wyświetlenia: własny (z pliku) albo domyślny; bez opisu zwraca sam klucz."""
    if key in _overrides:
        return _overrides[key]
    return info(key)[0] or key


def has_description(key):
    return key in _overrides or bool(info(key)[0])


def unit_of(key):
    return info(key)[1]


def group_of(key):
    return info(key)[3]


def is_alarm(key):
    return "alarm" in key


# ---------------------------------------------------------------- formatowanie wartości
def _fmt_duration(sec):
    sec = int(sec)
    d, rest = divmod(sec, 86400)
    h, rest = divmod(rest, 3600)
    m, s = divmod(rest, 60)
    if d:
        return f"{d} d {h} h {m} min"
    if h:
        return f"{h} h {m} min {s} s"
    if m:
        return f"{m} min {s} s"
    return f"{s} s"


NO_SENSOR = "brak czujnika"


def with_unit(key, text):
    """Dopisuje jednostkę do sformatowanej wartości (nie dla „—” i „brak czujnika”)."""
    unit = unit_of(key)
    return f"{text} {unit}" if unit and text not in ("—", NO_SENSOR) else text


def format_param(key, raw):
    """Czytelny tekst wartości (bez jednostki)."""
    if raw is None:
        return "—"
    s = str(raw).strip()
    if s == "":
        return NO_SENSOR if info(key)[1] == "°C" and not key.endswith("_cal") else "—"
    if key in ENUMS:
        return ENUMS[key].get(s, f"Nieznany ({s})")
    _, unit, kind, _ = info(key)
    if kind == "onoff":
        return _ON_OFF.get(s, f"Nieznany ({s})")
    if kind == "yesno":
        return {"0": "Nie", "1": "Tak"}.get(s, s)
    if kind == "unix":
        try:
            f = float(s)
            if f <= 0:
                return "—"
            dt = datetime.datetime.fromtimestamp(f, tz=datetime.timezone.utc).astimezone()
            return dt.strftime("%d-%m-%Y %H:%M")
        except (ValueError, OverflowError, OSError):
            return "—"
    if kind == "dur":
        try:
            return _fmt_duration(float(s))
        except ValueError:
            return s
    if kind == "text" or len(s) > 20:
        return s if len(s) <= 60 else s[:40] + "…"
    try:
        f = float(s)
    except ValueError:
        return s if len(s) <= 60 else s[:40] + "…"
    if f == int(f):
        return str(int(f))
    if unit == "°C" and not key.endswith("_cal"):
        return f"{f:.1f}"
    return f"{f:.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------- układ zakładki „Odczyty”
GROUPS = {
    "Temperatury": ["tkot_value", "tpow_value", "tcwu_value", "tsp_value", "tzew_value",
                    "t1_value", "t2_value", "tpod_value", "twew_value"],
    "Nastawy": ["kot_tzad", "kot_tact", "cwu_tzad", "cwu_tact", "ob1_tzad", "ob2_tzad",
                "ob1_zaw4d_tzad", "ob1_pok_tzad", "ob2_pok_tzad", "kot_tmin", "tpow_min"],
    "Palnik i paliwo": ["pl_status", "pl_status_ext", "pl_power_kw", "pl_flame", "pl_fuel_flow",
                        "fuel_level", "time_to_empty", "next_fuel_time", "add_fuel", "add_fuel_time",
                        "act_dm_speed", "mpl_dm_rpm", "mpl_temp"],
    "Wyjścia (stan urządzeń)": ["out_pomp1", "out_pomp2", "out_cwu", "out_miesz", "out_pod",
                                "out_dm", "out_zaw4d", "out_aux"],
    "Wejścia cyfrowe": ["di_zawl", "di_zas", "di_alarm", "di_termik", "di_stb", "di_term1", "di_term2"],
    "Obwód CO 1": ["ob1_typ", "ob1_tzad", "ob1_tmax", "ob1_zaw4d_tzad", "ob1_zaw4d_pos", "ob1_zaw4d_max",
                   "ob1_pomp_on", "ob1_pomp_off", "ob1_pok_tact", "ob1_pok_tzad", "ob1_pok_heat"],
    "Obwód CO 2": ["ob2_typ", "ob2_tzad", "ob2_tmax", "ob2_pomp_on", "ob2_pomp_off",
                   "ob2_pok_tact", "ob2_pok_tzad", "ob2_pok_heat"],
    "CWU i cyrkulacja": ["fun_cwu", "cwu_state", "cwu_out_state", "cwu_tobn", "cwu_st_tobn"],
    "Tryb pracy": ["zima_lato", "zima_lato_state", "tryb_auto_state", "autolato_tzew", "autolato_hist",
                   "pog_en", "pog_krzyw1", "pog_krzyw2", "power_state"],
    "Podajnik i kalibracja": ["pod_run_time", "pod_run_time_last", "pod_tmax", "pl_calib_en",
                              "pl_calib_time", "pl_calib_perf", "pl_fuel_calor"],
    "Czyszczenie i licznik": ["clean_act_kg", "clean_exch_kg", "clean_burn_time", "pl_tptotal"],
    "Termostat RF (BT4)": ["rf86_temp", "rf86_rh", "rf86_bat", "rf86_sig", "rf86_v"],
    "Alarmy – czujniki": ["alarm_tkot", "alarm_tpow", "alarm_tpod", "alarm_tcwu", "alarm_twew",
                          "alarm_tzew", "alarm_t1", "alarm_t2", "alarm_tsp"],
    "Alarmy": ["alarm_rozp", "alarm_rozp_ext", "alarm_pod_zaplon", "alarm_tkot_90", "alarm_tpod_hi",
               "alarm_tco1_hi", "alarm_termik", "alarm_stb", "alarm_zew", "alarm_zasobnik",
               "alarm_otw_zasob", "alarm_poz_ruszt", "alarm_cis", "alarm_clean_exch", "alarm_clwym",
               "alarm_ipconflict", "dp_alarm", "mpl_alarm"],
    "Urządzenie": ["device_name", "device_type", "device_soft_version", "device_hard_version",
                   "eth_ip", "datetime", "remote_server_status"],
}

# alarmy mają własną zakładkę „Alarmy”; zakładka „Odczyty” pokazuje pozostałe grupy
ALARM_GROUP_NAMES = ("Alarmy", "Alarmy – czujniki")
ALARM_GROUPS = {g: GROUPS[g] for g in ALARM_GROUP_NAMES}
READING_GROUPS = {g: k for g, k in GROUPS.items() if g not in ALARM_GROUP_NAMES}

# wszystkie alarmy (do powiadomień i zakładki „Alarmy”)
ALARM_KEYS = [k for g in ALARM_GROUP_NAMES for k in GROUPS[g]]

# kolumny pliku CSV z historią (ten sam zestaw co zakładka „Odczyty”)
CSV_KEYS = []
for _name, _keys in GROUPS.items():
    if _name == "Urządzenie":
        continue
    for _k in _keys:
        if _k not in CSV_KEYS:
            CSV_KEYS.append(_k)
