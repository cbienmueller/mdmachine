"""tasks.py
Erhält konkrete Aufgaben von mdmachine, 
die dort über Kommandozeilenparameter ausgewählt wurden.
"""

# Batteries included
import time
import uuid

# MDMWRX
from mdmwrx.task_sidefiles import make_sidebar_file, make_sitemap_n_timeline
from mdmwrx.task_file import handle_file
from mdmwrx.tools import alte_Dateien_entfernen
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
                    alte_Dateien_entfernen(path, 0, True)
                    exit()
    print("Schritt 4:\n\tAlte Dateien löschen!\n")
    alte_Dateien_entfernen(path, 0, True, True)
    

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
            alte_Dateien_entfernen(path, c_o.poll_generation - 2)
        elif not c_o.poll_generation:   # polling setzt generation auf positiven Wert, dann wird woanders gewartet!
            print("Kurze Ruhepause für die Cloud, danach Löschen alter Dateien.")
            try:
                time.sleep(10)   # Abstand zwischen Doppelkonvertierungen um Cloudsync. zu schonen
            except KeyboardInterrupt:
                print("\nPause abgebrochen. Kein Problem, lösche noch eventuelle mdm_old-Dateien.")
                alte_Dateien_entfernen(path, 0)
                print("Fertig & beendet (wegen KeyboardInterrupt)")
                exit()
            alte_Dateien_entfernen(path, c_o.poll_generation - 2)
        
    if not be_quiet:
        if subdirs:
            print(f'''  * Dir "{indent}{path.name}" bearbeitet: {subdirs} direkte Unterverzeichnisse bearbeitet''')
        elif not konvertierte and do_recursive:
            print(f'''  * Dir "{indent}{path.name}" bearbeitet: Nichts zu tun gewesen''')
        
    return konvertierte


def handle_polling(c_o, startpath, do_sidebar=False, do_force=False, do_recursive=False):
    poll_flag_filename = "_mdm_poll_" + uuid.uuid4().hex + ".flag"
    print('Funktion: Polling')
    for f in startpath.glob('_mdm_poll_*.flag'):
        print(f"Fremdes polling flag gefunden! {f.name} muss gelöscht werden ")
        f.unlink()
        print("Warte pauschal 10s, dass eventuelle Konvertierungen beendet werden...")
        time.sleep(10)
    # Sauberer Start
    alte_Dateien_entfernen(startpath, 0, do_recursive=do_recursive, remove_temps=True)
    c_o.poll_generation = 2  # virtueller Vorgänger > 0, den vor der Action wird poll_generation noch inkrementiert!
    with (startpath / poll_flag_filename).open('w') as f:
        f.write('polling')
    TIMERSTARTWERT = 20  # Sekunden, bis auch alte Backupdateien gelöscht werden
    timer = TIMERSTARTWERT
    be_quiet = False
    do_print = True
    while (startpath / poll_flag_filename).is_file():   # Ende, wenn MEIN Flag gelöscht wird!
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
            c_o.poll_generation += 1          
            # also sind 3 Generationen noch auf der Festplatte: -1, -2 und -3! -0 wird als nächstes angelegt
            alte_Dateien_entfernen(startpath, c_o.poll_generation - 3, do_recursive)  # jetzt also noch -1 und -2
            timer = TIMERSTARTWERT / 2
            if do_recursive:
                print('\nNun wird der Verzeichnisbaum alle 3s still überprüft und ggf. konvertiert.\nEnde mit Strg-C\n')
            else:
                print('\nNun wird das Verzeichnis alle 3s still überprüft und ggf. konvertiert.\nEnde mit Strg-C\n')
        else:
            try:
                time.sleep(3)
                if c_o.poll_generation > 2:  # Denn bei 2 ist noch nix konvertiert worden...
                    timer -= 3
                    if timer <= 0:
                        anzahl, nextanzahl = alte_Dateien_entfernen(startpath, c_o.poll_generation - 2, do_recursive)  
                        # jetzt nur noch -1 auf der Platte
                        c_o.poll_generation += 1  # skip, um später weiter zu löschen
                        if not nextanzahl:  # oops, -1 ist leer! beim letzten Mal schon geskipped?
                            c_o.poll_generation = 2   # Neustart
                            # print("    -> Polling-Generation-Zähler zurückgesetzt.")
                        timer = TIMERSTARTWERT
            except KeyboardInterrupt:
                print("\nPause abgebrochen. Kein Problem, lösche noch eventuelle mdm_old-Dateien.")
                alte_Dateien_entfernen(startpath, 0, do_recursive)  # Alle löschen
                print("Fertig & beendet (wegen KeyboardInterrupt)")
                (startpath / poll_flag_filename).unlink()      # jetzt belege ich das Verzeichnis nicht mehr...
                exit()

    print('Mein Polling-Flag wurde gelöscht!\nEnde des Programms.')
    alte_Dateien_entfernen(startpath, 0, do_recursive)  # Alle löschen
    exit()

