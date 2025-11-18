#!/usr/bin/env python3

""" mdmachine
    Konvertiert Markdown-Dateien mit Docker in html und PDF
    Genutzt werden derzeit (2025-08-09)
        + pandoc lokal installiert (per Parameter auch per Docker)
        + google chrome lokal installiert 
        + Java, Python als Apps 
        + lokal: Dateien zur Anreicherung von HTML
        + online: meine oder deine CSS-Dateien und Fonts
    Die eigentlichen Funktionen sind in das package mdmwrx ausgelagert.
"""

# Batteries included
import sys

from pathlib import Path
from argparse import ArgumentParser

# MDMWRX
import mdmwrx.tasks
import mdmwrx.task_file
from mdmwrx.task_sidefiles import make_sidebar_file
from mdmwrx.config import get_config_obj
from mdmwrx.tools import debug, write_demo_mdm_dir_yaml, write_demo_mdm_root_yaml

HELP = '''
    konvertiert Markdown-Datei(en)
        * mit Präprozessor (inkl. Ausführen von Codeblöcken und Mermaid-Code)
        * und biec-Customizing (CSS)
        * via pandoc in HTML und 
        * via Chrome in Din-A4-PDF, wenn die md-Datei neuer als die HTML-Zieldatei ist.
        * Mit m²_generate_slides im YAML-Block wird zusätzlich ein SLIDES-PDF erzeugt.
    Aufruf alternativ mit...
        --all               Zum einmaligen Konvertieren aller Dateien des akt. Verzeichnisses.
        --poll              Für dauerhaftes Polling des akt. Verzeichnisses.*
        --sidebar           Zum Erzeugen einer neuen _mdm_sidebar_.html.
        <datei.md>          Zum Konvertieren genau einer Quell-Datei.
        --force <datei.md>  Erzwingt diese Konvertierung, auch wenn Datei unverändert.
        --help              Automatisch generierte Hilfe zu den Parametern.
        --recursive         Bearbeitet auch Unterverzeichnisse
        --demodirinfo       Gibt eine inaktive, kommentierte mdm_dir.yaml.blank zum Editieren aus.
        --update            Prüft ob im aktuellen Verzeichnis mdm_root.yaml steht.
                            Wenn ja, wird der ganze Verzeichnisbaum ab hier nach unten
                            konvertiert, sidebars und ggf. eine sitemap angelegt.
        
        *   Verzeichnisbearbeitung mit polling ohne Unterverzeichnisse. 
            _dateiname_.md wird immer übersprungen (gut für reine include-Dateien) wenn nicht explizit aufgerufen.
        
    DryRun ("was wäre wenn") im Verzeichnis\n    {}:
        '''


def start_your_engines():
    Path('/tmp/mdmachine/config').mkdir(parents=True, exist_ok=True)
    Path('/tmp/mdmachine/cache').mkdir(parents=True, exist_ok=True)

    # Pfad, in dem Medien-Dateien liegen, hauptsächlich CSS-Includes
    medien_path: Path = (Path(__file__).parent.resolve() / "mdmwrx" / "medien").absolute()
    print(f'Medienverzeichnis:  {medien_path}')

    # Arbeitspfad ("von wo wurde mdmachine aufgerufen, wo liegen die Dateien")
    startpath = Path(".").resolve()
    config_obj = get_config_obj(startpath, medien_path)  # Klärt z.B. wo root liegt und liest dort abgelegte Konfig ein

    parser = ArgumentParser()

    parser.add_argument("-v", "--verbosity", dest="verbosity_flag",
                        action="store_const", const=True, default=False,
                        help="Setze verbosity hoch für Zusatzinfos")                    
    parser.add_argument("-f", "--force", dest="force_flag", 
                        action="store_const", const=True, default=False, 
                        help="Erzwinge Konvertierung")
    parser.add_argument("-a", "--all", dest="all_flag", 
                        action="store_const", const=True, default=False, 
                        help="Bearbeite ganzes Verzeichnis")
    parser.add_argument("-s", "--sidebar", dest="side_flag", 
                        action="store_const", const=True, default=False, 
                        help="Erstelle eine _mdm_sidebar_.html. Vorhandene mdm_dir.yaml wird ausgewertet!")
    parser.add_argument("-p", "--poll", dest="poll_flag", 
                        action="store_const", const=True, default=False, 
                        help="Überprüfe Verzeichnis fortlaufend auf Änderungen")
    parser.add_argument("-r", "--recursive", dest="recursive_flag", 
                        action="store_const", const=True, default=False, 
                        help="mit Unterverzeichnissen")
    parser.add_argument("-u", "--update", dest="update_flag", 
                        action="store_const", const=True, default=False, 
                        help="Update für den ganzen Verzeichnisbaum ab `root`:"
                             " Konvertiere alle geänderten md-Dateien, erzeuge sidebars und eine sitemap")
    parser.add_argument("--demo_mdm_dir", dest="demo_mdm_dir_flag", 
                        action="store_const", const=True, default=False, 
                        help="Gibt eine kommentierte mdm_dir.yaml.blank zum Editieren aus (ggf. in übergebenem Verzeichnis)")
    parser.add_argument("--demo_mdm_root", dest="demo_mdm_root_flag", 
                        action="store_const", const=True, default=False, 
                        help="Gibt eine kommentierte mdm_root.yaml.blank zum Editieren aus (ggf. in übergebenem Verzeichnis)")
    parser.add_argument("file_names", type=str, nargs="*")

    mdm_args = parser.parse_args()

    if len(sys.argv) <= 1:
        print(HELP.format(startpath))
        mdmwrx.tasks.handle_dir(config_obj, startpath, dryrun=True)
        print("Es wurde keine Konvertierung durchgeführt, da kein Parameter angegeben wurde.")
        exit(0)

    if not config_obj.flag_verbose:
        config_obj.flag_verbose = mdm_args.verbosity_flag

    for file_name in (mdm_args.file_names if mdm_args.file_names else ['.']):
        flag_is_source_file = False
        sourcefile = Path(file_name).resolve()
        if not sourcefile.exists():
            print(f'''Datei/Verzeichnis nicht gefunden:\n\t{sourcefile}\n\tSkipping...''')
            continue
            
        if sourcefile.is_file():
            startpath = sourcefile.parent.resolve()
            flag_is_source_file = True
            debug(config_obj, f'Arbeite mit Datei-Pfad {startpath}')

        elif sourcefile.is_dir():
            startpath = sourcefile.resolve()
            if mdm_args.demo_mdm_dir_flag:
                print(write_demo_mdm_dir_yaml(startpath) + ' geschrieben')
            elif mdm_args.demo_mdm_root_flag:
                print(write_demo_mdm_root_yaml(startpath) + ' geschrieben')
            else:
                debug(config_obj, f'Arbeitsverzeichnis: {startpath}')

        else:
            continue  # was immer weder file noch dir sein soll
    
        if mdm_args.update_flag:
            mdmwrx.tasks.handle_update(config_obj, startpath, mdm_args.force_flag, mdm_args.poll_flag)  
            # Endlos mit poll_flag, daher Option unten palmäßig nicht mehr erreichbar.
            
        if mdm_args.all_flag:
            mdmwrx.tasks.handle_dir(config_obj, startpath, 
                                    do_sidebar=mdm_args.side_flag, do_force=mdm_args.force_flag,
                                    do_recursive=mdm_args.recursive_flag)
            continue
            
        if mdm_args.side_flag:
            make_sidebar_file(config_obj, startpath, do_recursive=mdm_args.recursive_flag)
            continue

        if mdm_args.poll_flag:                                                                          # kommt nicht zurück
            mdmwrx.tasks.do_poll(config_obj, 
                                 startpath,
                                 do_force=mdm_args.force_flag,
                                 do_recursive=mdm_args.recursive_flag)
            
        if flag_is_source_file:
            erfolg, _ = mdmwrx.task_file.handle_file(config_obj, sourcefile, do_force=mdm_args.force_flag)
            if not erfolg:
                print(f'Datei {sourcefile.name} nicht gefunden oder keine Markdowndatei\n Optionen: <Dateiname> | --polling')
            else:
                mdmwrx.task_file.alte_Dateien_entfernen(startpath)
            

# ############# #
# ### START ### #
# ############# #

print('mdmachine Version 1.0.RC11 von 2025-10-26')
start_your_engines()
        
