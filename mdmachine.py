#!/usr/bin/env python3

""" mdmachine
    Konvertiert Markdown-Dateien mit Docker in html und PDF
    Genutzt werden derzeit (2025-06-29)
        + pandoc via Docker
        + google chrome, Java, Python als Apps 
        + lokal: Dateien zur Anreicherung von HTML
        + online: meine CSS-Dateien und Fonts
    Viele Funktionen sind in das package mdmwrx ausgelagert.
    
"""
# Batteries included
import sys

from pathlib import Path
from argparse import ArgumentParser

# mdmaschine worx 
import mdmwrx.tasks
from mdmwrx.sidebar import write_demo_dir_info_yaml, \
    make_sidebar, make_new_sidenavi

# get_root_info, make_sitemap, get_folder_filename_title_yaml, \

# ############# #
# ### START ### #
# ############# #

print('mdmachine Version 0.9.24 von 2025-06-29: mit rekursivem polling')

Path('/tmp/mdmachine/config').mkdir(parents=True, exist_ok=True)
Path('/tmp/mdmachine/cache').mkdir(parents=True, exist_ok=True)

# Pfad, in dem Medien-Dateien liegen, hauptsächlich CSS-Includes
mdmwrx.tasks.medien_path: Path = (Path(__file__).parent.resolve() / "mdmwrx" / "medien").absolute()
print(f'Medienverzeichnis:  {mdmwrx.tasks.medien_path}')

# Arbeitspfad ("von wo wurde mdmachine aufgerufen, wo liegen die Dateien")
startpath = Path(".").resolve()

do_sidebar = False
parser = ArgumentParser()
                    
parser.add_argument("-f", "--force", dest="force_flag", 
                    action="store_const", const=True, default=False, 
                    help="Erzwinge Konvertierung")
parser.add_argument("-a", "--all", dest="all_flag", 
                    action="store_const", const=True, default=False, 
                    help="Bearbeite ganzes Verzeichnis")
parser.add_argument("-s", "--sidebar", dest="side_flag", 
                    action="store_const", const=True, default=False, 
                    help="Erstelle eine sidebar.html. Vorhandene dir_info.yaml wird ausgewertet!")
parser.add_argument("-n", "--sidenavi", dest="sidenavi_flag", 
                    action="store_const", const=True, default=False, 
                    help="Erstelle eine sidenavi.html. Vorhandene dir_info.yaml wird ausgewertet!")
parser.add_argument("-w", "--web", dest="web_flag", 
                    action="store_const", const=True, default=False, 
                    help="Kombiniere poll und sidebar")
parser.add_argument("-p", "--poll", dest="poll_flag", 
                    action="store_const", const=True, default=False, 
                    help="Überprüfe Verzeichnis fortlaufend auf Änderungen")
parser.add_argument("-r", "--recursive", dest="recursive_flag", 
                    action="store_const", const=True, default=False, 
                    help="mit Unterverzeichnissen")
parser.add_argument("-u", "--update", dest="update_flag", 
                    action="store_const", const=True, default=False, 
                    help="update whole directory tree: Markdown files, sidebars and sitemap")
parser.add_argument("--sitemap", dest="sitemap_flag", 
                    action="store_const", const=True, default=False, 
                    help="legt sitemap.html an")
parser.add_argument("--demodirinfo", dest="demo_dir_info_flag", 
                    action="store_const", const=True, default=False, 
                    help="Gibt eine kommentierte dir_info.yaml.blank zum Editieren aus (ggf. in übergebenem Verzeichnis)")
parser.add_argument("file_names", type=str, nargs="*")

mdm_args = parser.parse_args()

sitemap_flag = False

if len(sys.argv) > 1:
    if mdm_args.sitemap_flag:
        mdmwrx.tasks.handle_sitemap(startpath)
        exit()
        
    for file_name in (mdm_args.file_names if mdm_args.file_names else ['.']):
        flag_is_source_file = False
        sourcefile = Path(file_name).resolve()
        if not sourcefile.exists():
            print(f'''Datei/Verzeichnis nicht gefunden:\n\t{sourcefile}\n\tSkipping...''')
            continue
            
        if sourcefile.is_file():
            startpath = sourcefile.parent.resolve()
            flag_is_source_file = True
            print(f'Arbeite mit Datei-Pfad {startpath}')

        elif sourcefile.is_dir():
            startpath = sourcefile.resolve()
            if mdm_args.demo_dir_info_flag:
                print(write_demo_dir_info_yaml(startpath) + ' geschrieben')
            else:
                print(f'Arbeitsverzeichnis: {startpath}')

        else:
            continue  # was immer weder file noch dir sein soll
    
        if mdm_args.update_flag:
            mdmwrx.tasks.handle_update(startpath, mdm_args.force_flag, mdm_args.poll_flag)  
            # Endlos mit poll_flag, daher Option unten palmäßig nicht mehr erreichbar.
            
        if mdm_args.all_flag:
            mdmwrx.tasks.handle_dir(startpath, 
                                    do_sidebar=mdm_args.side_flag, do_force=mdm_args.force_flag,
                                    do_recursive=mdm_args.recursive_flag)
            continue
            
        if mdm_args.side_flag:
            make_sidebar(startpath, do_recursive=mdm_args.recursive_flag)
            continue

        if mdm_args.sidenavi_flag:
            make_new_sidenavi(startpath)
            continue
            
        if mdm_args.poll_flag:                                                                          # kommt nicht zurück
            mdmwrx.tasks.do_poll(startpath,
                                 do_force=mdm_args.force_flag,
                                 do_recursive=mdm_args.recursive_flag)
            
        if mdm_args.web_flag:                                                                           # kommt nicht zurück
            mdmwrx.tasks.do_poll(startpath,
                                 do_sidebar=True,
                                 do_force=mdm_args.force_flag,
                                 do_recursive=mdm_args.recursive_flag)
            
        if flag_is_source_file:
            erfolg, _ = mdmwrx.tasks.handle_file(sourcefile, do_force=mdm_args.force_flag)
            if not erfolg:
                print(f'Datei {sourcefile.name} nicht gefunden oder keine Markdowndatei\n Optionen: <Dateiname> | --polling')
            else:
                mdmwrx.tasks.alte_Dateien_entfernen(startpath)
            
else:
    print(f'''
konvertiert Markdown-Datei(en)
    * mit Präprozessor (inkl. Ausführen von Codeblöcken und Mermaid-Code)
    * und biec-Customizing (CSS)
    * via pandoc in HTML und 
    * via Chrome in Din-A4-PDF, wenn die md-Datei neuer als die HTML-Zieldatei ist.
    * Mit generate_slides in YAML wird zusätzlich ein SLIDES-PDF erzeugt.
Aufruf alternativ mit...
    --all               Zum einmaligen Konvertieren aller Dateien des akt. Verzeichnisses.
    --poll              Für dauerhaftes Polling des akt. Verzeichnisses.*
    --sidebar           Zum Erzeugen einer neuen sidebar.html.
    --web               Kombiniert --poll mit --sidebar (letzteres nur nach erfolgter Konvertierung).*
    <datei.md>          Zum Konvertieren genau einer Quell-Datei.
    --force <datei.md>  Erzwingt diese Konvertierung, auch wenn Datei unverändert.
    --help              Automatisch generierte Hilfe zu den Parametern.
    --recursive         Bearbeitet auch Unterverzeichnisse
    --demodirinfo       Gibt eine inaktive, kommentierte dir_info.yaml.blank zum Editieren aus.
    --sitemap           Prüft ob aktuelle dir_info.yaml das flag isroot hat. 
                        Dann erzwingt es sidebar mit recursive und 
                        legt dabei zusätzlich eine sitemap.html an.
    
    *   Verzeichnisbearbeitung mit polling ohne Unterverzeichnisse. 
        _dateiname_.md wird immer übersprungen (gut für reine include-Dateien) wenn nicht explizit aufgerufen.
    
DryRun ("was wäre wenn") im Verzeichnis\n    {startpath}:
    ''')
    mdmwrx.tasks.handle_dir(startpath, dryrun=True)
    print("Keine Konvertierung wurde durchgeführt, da kein Parameter angegeben wurde.")
    
