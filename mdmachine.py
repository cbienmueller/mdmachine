#!/usr/bin/python3

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
import time
from datetime import datetime
import uuid
import shutil

from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass

# mdmaschine worx 
from mdmwrx.pre_proc import do_pre_proc
from mdmwrx.yamlread import get_yaml_dict_from_md 
from mdmwrx.sidebar import write_demo_dir_info_yaml, \
    get_root_info, get_folder_filename_title_yaml, \
    make_sidebar, make_sitemap, make_new_sidenavi
from mdmwrx.converter import do_convert, SLIDE_FORMATE

lastconverted = {}


def check_if_path_is_root(path):
    _, _, yd = get_folder_filename_title_yaml(path)
    isrootflag = yd.get("m²-isroot")
    return isrootflag

    
def handle_update(path, force_flag, poll_flag):
    print("\nGewählte Funktion: Update - überprüft gesamten Dokumentenbaum.\n")
    if not check_if_path_is_root(path):
        print('Das aktuelle Verzeichnis ist nicht in seiner dir_info.yaml als Root deklariert.\n'
              'Daher wird kein Komplett-Update durchgeführt.\nLösung:\n'
              ' * Setzte zuerst "isroot: True" oder\n'
              ' * Wechsle in das Rootverzeichnis der Dokumente')
        exit()
    print("Schritt 1:\nRekursiv alle Markdowndateien prüfen/ggf. konvertieren\n sowie dann auch sidebar.html aktualisieren.\n")
    handle_dir(path, do_print=False,
               do_sidebar=True, do_force=force_flag,
               do_recursive=True)
    print("Schritt 2:\nsitemap.html erstellen\n")
    make_sitemap(path)
    print("Fertig zum Upload!")
    if poll_flag:
        print("\nGewählte Funktion: Polling - überprüft still gesamten Dokumentenbaum alle 5 Sekunden bis zu CTRL-C!\n")
        while True:  
            konvertierte = handle_dir(path, do_print=False,
                                      do_sidebar=True, do_force=False,
                                      do_recursive=True, be_quiet=True)
            if konvertierte:
                print("Folgeaufgabe wg. Konvertierung: sitemap.html erstellen\n")
                make_sitemap(path)
                print("Nun wieder stilles Polling")
            else:
                try:
                    time.sleep(5)
                except KeyboardInterrupt:
                    print("\nPolling abgebrochen. Kein Problem...")
                    exit()
        
    
def handle_sitemap(path):
    if not check_if_path_is_root(path):
        print('Das aktuelle Verzeichnis ist nicht in seiner dir_info.yaml als Root deklariert.\n'
              'Daher wird keine sitemap erstellt.\nLösung:\n'
              ' * Setzte zuerst "isroot: True" oder\n'
              ' * Wechsle in das Rootverzeichnis der Dokumente')
        exit()
    make_sitemap(path)
    
    
def handle_dir(path, do_print=True, dryrun=False, do_sidebar=False, do_force=False, do_recursive=False, 
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
                _, n = handle_file(sourcefile, do_print, dryrun, do_force)
                konvertierte += n
            elif do_recursive and sourcefile.is_dir():
                konvertierte += handle_dir(sourcefile, 
                                           do_print, dryrun, do_sidebar, do_force, do_recursive,
                                           indent="  " + indent, be_quiet=be_quiet)
                subdirs += 1
        elif dryrun:
            if not be_quiet:
                print(f'  * Filename:  {sourcefile.name: <38} wird wegen des Namens übersprungen!')
            
    if konvertierte:
        if do_sidebar:
            make_sidebar(path)
        elif (path / "dir_info.yaml").exists():  # Die Datei ist ja nicht ohne Grund da...
            make_sidebar(path, talk="auto-sidebar, da dir_info.yaml existiert")
        elif (path / "sidebar.html").exists():  # Die Datei ist ja nicht ohne Grund da...
            make_sidebar(path, talk="auto-sidebar, da sidebar.html bereits existiert")
        if do_recursive:
            alte_Dateien_entfernen(path)
        else:
            print("Kurze Ruhepause für die Cloud, danach Löschen alter Dateien.")
            try:
                time.sleep(10)   # Abstand zwischen Doppelkonvertierungen um Cloudsync. zu schonen
            except KeyboardInterrupt:
                print("\nPause abgebrochen. Kein Problem, lösche trotzdem schnell mdmold-Dateien.")
                alte_Dateien_entfernen(path)
                print("Fertig & beendet (per KeyboardInterrupt)")
                exit()
            alte_Dateien_entfernen(path)
        
    if not be_quiet:
        if subdirs:
            print(f'''  * Dir "{indent}{path.name}" bearbeitet: {subdirs} direkte Unterverzeichnisse bearbeitet''')
        elif not konvertierte and do_recursive:
            print(f'''  * Dir "{indent}{path.name}" bearbeitet: Nichts zu tun gewesen''')
        
    return konvertierte


def alte_Dateien_entfernen(path):
    for oldfile in path.iterdir():
        if oldfile.is_file() and \
           oldfile.stem.startswith("_mdmold_"):
            print(f"    Entferne vorherige Version ({oldfile.name}).")
            oldfile.unlink(missing_ok=True)
    
    
@dataclass
class MdYamlMeta:  
    title: str = ""
    force_title: bool = False
    gen_slides_flag: bool = False
    keep_slides_html_flag: bool = False
    suppress_pdf_flag: bool = False
    lang: str = ""
       
    
@dataclass
class ConvertData:
    path: Path
    medien_path: Path
    tmp_filestem: str
    mymeta: MdYamlMeta
    
        
def get_meta_from_mdyaml(mdfile):
    """ - Liefert eine Auswahl an verwertbaren Metadaten als MdYamlMeta-Objekt
          - s.o.
        - sowie includierte md-Dateien als String-Liste
        
        Der Titel wird aus dem YAML-Bereich der MD-Datei extrahiert.
        Wenn nicht vorhanden, so wird der Dateiname ohne Extension 
        als Ersatz gewählt.
        
        generateslides ist eine eigene Variable, 
            die auch als String als True gilt, wenn das erste Zeichen passt zu : true, yes, ja, 1, keep
            Wenn sie mit k oder K (keep) beginnt, wird die temporäre HTML-Datei nicht gelöscht.
    """
    mymeta = MdYamlMeta()
    mymeta.inc_style_list = []

    yaml_dict = get_yaml_dict_from_md(mdfile)
    includes = []

    # print(yaml_dict)    # nur für debugging
    if yaml_dict:
        gen_slides_value = yaml_dict.get("m²-generate-slides")
        if gen_slides_value and str(gen_slides_value)[0].lower() in ("t", "y", "j", "1", "k"):
            mymeta.gen_slides_flag = True
            if str(gen_slides_value)[0].lower() == "k":
                mymeta.keep_slides_html_flag = True
        mymeta.lang = yaml_dict.get("lang")
        mymeta.title = yaml_dict.get("title")
        # print("YAML-title: ", mymeta.title)
        mymeta.suppress_pdf_flag = yaml_dict.get("m²-suppress-pdf", False)
        includes = yaml_dict.get("m²-include-after")
        if isinstance(includes, str):
            includes = [includes]
        if not isinstance(includes, list):
            includes = []
        
        # Nun eine Liste einzufügender Style-Schnipsel-Dateien
        i_s = yaml_dict.get("m²-include-style")
        if isinstance(i_s, list):
            mymeta.inc_style_list = [str(x).lower() for x in i_s]
        elif i_s:
            mymeta.inc_style_list = [str(i_s).lower()]
        else:
            mymeta.inc_style_list = []      # Dummywert
        
        # Nun eine Liste der zu erzeugenden Slide-Formate mit mindestens einem Wert drin.
        s_f = yaml_dict.get("m²-slide-format")
        if isinstance(s_f, list):
            mymeta.slide_format_list = [str(x).lower() for x in s_f]
        elif s_f:
            mymeta.slide_format_list = [str(s_f).lower()]
        else:
            mymeta.slide_format_list = ["a5"]    # Dummywert, quasi Din-A5 quer entspricht iPad air gen 5
            
    if not mymeta.title:
        mymeta.title = mdfile.stem
        mymeta.force_title = True

    return mymeta, includes
    
    
def handle_file(sourcefile, do_print=True, dryrun=False, do_force=False):
    """gibt (bool erfolg, int anzahl) zurück"""
    flag_do_convert = False
    if not (sourcefile.is_file() and 
            sourcefile.suffix.lower() in (".md", ".markdown")):
        return False, 0

    path = sourcefile.parent.absolute()
    
    if do_print:
        # print(f"Jetzt:     {''              : <20}  time:{int(time.time()) : >12}")
        print(f'''src>: {sourcefile.name: <38} mtime: {
            datetime.fromtimestamp(sourcefile.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}''')
    
    htmlfile = path / (sourcefile.stem + ".html")
    if htmlfile.exists():
        lasttime = lastconverted.get(sourcefile.absolute(), 0)
        if lasttime and lasttime < sourcefile.stat().st_mtime:
            flag_do_convert = True
            print("")
            print(f'src>: {sourcefile.name: <38} ist neuer als '
                  'der Beginn der letzten Konvertierung. Konvertiere sofort!')
        elif htmlfile.stat().st_mtime < sourcefile.stat().st_mtime + 3:
            print(f'>trg: {htmlfile.name: <38} älter als Quelldatei {sourcefile.name} + 3 Sekunden.')
            while sourcefile.stat().st_mtime + 3 > int(time.time()):
                wartezeit = int(min(5 - (time.time() - sourcefile.stat().st_mtime), 4))
                print("Zu frisch - warte für " + str(wartezeit) + "s")
                try:
                    time.sleep(wartezeit)  # verhindert Doppeltkonvertierungen und Synchronisationschaos...
                except KeyboardInterrupt:
                    print("\nWartezeit abgebrochen. Kein Problem...")
                    exit()
            flag_do_convert = True

        elif do_print:
            print(f'''>trg: {htmlfile.name: <38} mtime: {
                datetime.fromtimestamp(htmlfile.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')} (keine Konv. nötig)''')
        
    else:
        print(f'>trg: {htmlfile.name: <38} zur Quelldatei {sourcefile.name} existiert nicht.')
        flag_do_convert = True
        
    if not do_force and not flag_do_convert or dryrun:
        return True, 0

    if not flag_do_convert:
        print(f'>trg: {htmlfile.name: <38} zur Quelldatei {sourcefile.name} wird wegen -f trotzdem erstellt.')
        
    #############################
    # Nun wird also konvertiert #
    #############################
    
    # Metadaten aus dem YAML-Bereich holen:
    mymeta, includes = get_meta_from_mdyaml(sourcefile)
    mymeta, includes = get_meta_from_mdyaml(sourcefile)
    
    if not mymeta.lang:
        mymeta.lang = get_root_info(path).lang
    
    tmp_filestem = "_mdmtemp_" + uuid.uuid4().hex
    tmp_preproc_file = path / f'{tmp_filestem}_preproc.md'
    tmp_concat_file = path / f'{tmp_filestem}_concat.md'
    # print("vermerke ", sourcefile.absolute(), time.time())
    lastconverted[sourcefile.absolute()] = time.time()
    
    print("Präprozessor...")
    do_pre_proc(sourcefile, tmp_preproc_file)
    
    if includes:
        for incname in includes:
            print(f'include-after: {incname}')
            incfile = path / incname
            if incfile.exists():
                do_pre_proc(incfile, tmp_concat_file, remove_yaml=True)
                with open(tmp_preproc_file, 'a') as prepro:
                    with open(tmp_concat_file, 'r') as concat:
                        prepro.write("\n \n \n")
                        shutil.copyfileobj(concat, prepro)
                tmp_concat_file.unlink(missing_ok=True)
            else:
                print(f'!!! include-file {incname} missing!!!')
                
    do_convert(ConvertData(path, medien_path, tmp_filestem, mymeta))  # Wenn Konvertierung nicht erfolgreich: Abbruch dort!
    
    endungen = ['_SLIDES.html', '_SLIDES.pdf', '.html', '_A4.pdf']
    for s_format in SLIDE_FORMATE.keys():
        endungen.append(f'_SLIDES_{s_format}.html')
        endungen.append(f'_SLIDES_{s_format}.pdf')
        
    for endung in endungen:

        # uralte immer entfernen (sollten anderweitig bereits entfernt worden sein)
        (path / f'_mdmold_{sourcefile.stem}{endung}').unlink(missing_ok=True)

        # alte immer umbenennen, auch wenn sie nicht ersetzt werden (dann müssen sie trotzdem weg)
        try:
            (path / f'{sourcefile.stem}{endung}').rename(path / f'_mdmold_{sourcefile.stem}{endung}')
        except FileNotFoundError:
            pass

    # neue - müssen eigentlich existieren (und im gleichen Filesystem liegen)!
    for endung in endungen:
        try:
            (path / f'{tmp_filestem}{endung}').rename(path / f'{sourcefile.stem}{endung}')
        except FileNotFoundError:
            pass

        if endung.startswith('_SLIDES') and endung.endswith('.html') and not mymeta.keep_slides_html_flag:
            (path / f'{sourcefile.stem}{endung}').unlink(missing_ok=True)

    # Sofort aufräumen, was nicht mehr gebraucht wird
    for tf in path.glob(f'{tmp_filestem}*'):
        try:
            tf.unlink()
        except Exception:
            pass
    return True, 1
    

def do_poll(startpath, do_sidebar=False, do_force=False, do_recursive=False):
    print('Funktion: Polling')
    k = 1
    handle_dir(startpath, do_sidebar=do_sidebar, do_force=do_force, do_recursive=do_recursive)   # force max beim ersten Mal
    while True:
        if k:
            if do_recursive:
                print('\nNun wird der Verzeichnisbaum alle 5s still überprüft und ggf. konvertiert.\nEnde mit Strg-C\n')
            else:
                print('\nNun wird das Verzeichnis alle 5s still überprüft und ggf. konvertiert.\nEnde mit Strg-C\n')
        else:
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                print("\nPolling abgebrochen. Kein Problem...")
                exit()
        k = handle_dir(startpath, do_print=False, do_sidebar=do_sidebar, do_recursive=do_recursive, be_quiet=True)   
        # hier kein do_force mehr, dafür immer quiet durch die Verzeichnisse...


# ############# #
# ### START ### #
# ############# #

print('mdmachine Version 0.9.24 von 2025-06-29: mit rekursivem polling')

Path('/tmp/mdmachine/config').mkdir(parents=True, exist_ok=True)
Path('/tmp/mdmachine/cache').mkdir(parents=True, exist_ok=True)

# Pfad, in dem Medien-Dateien liegen, hauptsächlich CSS-Includes
medien_path: Path = (Path(__file__).parent.resolve() / "mdmwrx" / "medien").absolute()
print(f'Medienverzeichnis:  {medien_path}')

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
        handle_sitemap(startpath)
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
            handle_update(startpath, mdm_args.force_flag, mdm_args.poll_flag)  
            # Endlos mit poll_flag, daher Option unten palmäßig nicht mehr erreichbar.
            
        if mdm_args.all_flag:
            handle_dir(startpath, 
                       do_sidebar=mdm_args.side_flag, do_force=mdm_args.force_flag,
                       do_recursive=mdm_args.recursive_flag)
            continue
            
        if mdm_args.side_flag:
            make_sidebar(startpath, do_recursive=mdm_args.recursive_flag)
            continue

        if mdm_args.sidenavi_flag:
            make_new_sidenavi(startpath)
            continue
            
        if mdm_args.poll_flag:
            do_poll(startpath, do_force=mdm_args.force_flag, do_recursive=mdm_args.recursive_flag)     # kommt nicht zurück
            
        if mdm_args.web_flag:                                                                           # kommt nicht zurück
            do_poll(startpath, do_sidebar=True, do_force=mdm_args.force_flag, do_recursive=mdm_args.recursive_flag)
            
        if flag_is_source_file:
            erfolg, _ = handle_file(sourcefile, do_force=mdm_args.force_flag)
            if not erfolg:
                print(f'Datei {sourcefile.name} nicht gefunden oder keine Markdowndatei\n Optionen: <Dateiname> | --polling')
            else:
                alte_Dateien_entfernen(startpath)
            
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
    handle_dir(startpath, dryrun=True)
    print("Keine Konvertierung wurde durchgeführt, da kein Parameter angegeben wurde.")
    
