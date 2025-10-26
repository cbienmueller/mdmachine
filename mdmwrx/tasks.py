"""tasks.py
Erhält konkrete Aufgaben von mdmachine, 
die dort über Kommandozeilenparameter ausgewählt wurden.
"""

# Batteries included
import time

# MDMWRX
from mdmwrx.task_sidefiles import make_sidebar_file, make_sitemap_n_timeline
from mdmwrx.task_file import handle_file, alte_Dateien_entfernen
# from mdmwrx.tools import debug


def handle_update(c_o, path, force_flag, poll_flag):
    print("\nGewählte Funktion: Update - überprüft gesamten Dokumentenbaum.\n")
    if not c_o.flag_dir_is_root:
        print('Das aktuelle Verzeichnis enthält keine mdm_root.yaml.\n'
              'Daher wird kein Komplett-Update durchgeführt.')
        exit()
        
    print("Schritt 1:\n\tRekursiv alle Markdowndateien prüfen/ggf. konvertieren\n")
    handle_dir(c_o, path, do_print=False,
               do_sidebar=True, do_force=force_flag,
               do_recursive=True)
               
    print("Schritt 2:\n\tsidebars rekursiv erzeugen")
    make_sidebar_file(c_o, path, do_recursive=True)
    
    if c_o.flag_gen_sitemap:
        print("Schritt 3:\n\tsitemap.html erstellen\n")
        make_sitemap_n_timeline(c_o, path)
    else:
        print("Schritt 3:\n\tsitemap.html erstellen ENTFÄLLT, da m²_generate_sitemap in mdm_root.yaml nicht gesetzt!\n")
        
    print("Fertig zum Upload!")
    if poll_flag:
        print("\nGewählte Funktion: Polling - überprüft still gesamten Dokumentenbaum alle 5 Sekunden bis zu CTRL-C!\n")
        while True:  
            konvertierte = handle_dir(c_o, path, do_print=False,
                                      do_sidebar=True, do_force=False,
                                      do_recursive=True, be_quiet=True)
            if konvertierte and c_o.flag_gen_sitemap:
                print("Folgeaufgabe wg. Konvertierung: sitemap.html erstellen\n")
                make_sitemap_n_timeline(c_o, path)
                print("Nun wieder stilles Polling")
            else:
                try:
                    time.sleep(5)
                except KeyboardInterrupt:
                    print("\nPolling abgebrochen. Kein Problem...")
                    exit()
        
    
def handle_dir(c_o, path, do_print=True, dryrun=False, do_sidebar=False, do_force=False, do_recursive=False, 
               indent="", be_quiet=False):
    konvertierte = 0
    subdirs = 0
    if do_recursive:
        if not be_quiet:
            print(f'''*** Dir "{indent}{path.name}" bearbeiten...''')
    for sourcefile in path.iterdir():
        if not (
                sourcefile.stem.startswith("_mdtemp") or sourcefile.stem.startswith("_mdmtemp") or
                (sourcefile.stem.startswith("_") and sourcefile.stem.endswith("_"))):
            if sourcefile.is_file():        
                _, n = handle_file(c_o, sourcefile, do_print, dryrun, do_force)
                konvertierte += n
            elif do_recursive and sourcefile.is_dir():
                konvertierte += handle_dir(c_o, sourcefile, 
                                           do_print, dryrun, do_sidebar, do_force, do_recursive,
                                           indent="  " + indent, be_quiet=be_quiet)
                subdirs += 1
        elif dryrun:
            if not be_quiet:
                print(f'  * Filename:  {sourcefile.name: <38} wird wegen des Namens übersprungen!')
            
    if konvertierte:
        if do_sidebar or \
           c_o.flag_gen_sidebar or \
           (path / "mdm_dir.yaml").exists() or \
           (path / "_mdm_sidebar_.html").exists():
            make_sidebar_file(c_o, path)
        if do_recursive:
            alte_Dateien_entfernen(path)
        else:
            print("Kurze Ruhepause für die Cloud, danach Löschen alter Dateien.")
            try:
                time.sleep(10)   # Abstand zwischen Doppelkonvertierungen um Cloudsync. zu schonen
            except KeyboardInterrupt:
                print("\nPause abgebrochen. Kein Problem, lösche noch eventuelle mdm_old-Dateien.")
                alte_Dateien_entfernen(path, True)
                print("Fertig & beendet (wegen KeyboardInterrupt)")
                exit()
            alte_Dateien_entfernen(path)
        
    if not be_quiet:
        if subdirs:
            print(f'''  * Dir "{indent}{path.name}" bearbeitet: {subdirs} direkte Unterverzeichnisse bearbeitet''')
        elif not konvertierte and do_recursive:
            print(f'''  * Dir "{indent}{path.name}" bearbeitet: Nichts zu tun gewesen''')
        
    return konvertierte


def do_poll(c_o, startpath, do_sidebar=False, do_force=False, do_recursive=False):
    print('Funktion: Polling')
    TIMERSTARTWERT = 30  # Sekunden, bis auch alte Backupdateien gelöscht werden
    timer = TIMERSTARTWERT
    be_quiet = False
    do_print = True
    while True:
        k = handle_dir(c_o, 
                       startpath, 
                       do_print=do_print,
                       do_sidebar=do_sidebar, 
                       do_force=do_force,              
                       do_recursive=do_recursive,
                       be_quiet=be_quiet)
        do_force = False  # force max nur beim ersten Mal
        do_print = False
        be_quiet = True  # volle Ausgabe max nur beim ersten Mal
        if k:
            timer = TIMERSTARTWERT
            if do_recursive:
                print('\nNun wird der Verzeichnisbaum alle 8s still überprüft und ggf. konvertiert.\nEnde mit Strg-C\n')
            else:
                print('\nNun wird das Verzeichnis alle 8s still überprüft und ggf. konvertiert.\nEnde mit Strg-C\n')
        else:
            try:
                time.sleep(8)
                timer -= 8
                if timer <= 0:
                    alte_Dateien_entfernen(startpath, False, do_recursive)
                    timer = TIMERSTARTWERT
            except KeyboardInterrupt:
                print("\nPause abgebrochen. Kein Problem, lösche noch eventuelle mdm_old-Dateien.")
                alte_Dateien_entfernen(startpath, True, do_recursive)
                print("Fertig & beendet (wegen KeyboardInterrupt)")
                exit()

