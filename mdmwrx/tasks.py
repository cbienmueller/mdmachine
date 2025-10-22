"""tasks.py
Erhält konkrete Aufgaben von mdmachine, 
die dort über Kommandozeilenparameter ausgewählt wurden.
"""

# Batteries included
import uuid
import shutil
import time
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path


from mdmwrx.pre_proc import do_pre_proc
from mdmwrx.yamlread import get_yaml_dict_from_md, get_yaml_value_2_list
from mdmwrx.converter import do_convert, SLIDE_FORMATE
from mdmwrx.sidebar import make_sidebar_file, make_sitemap_file
from mdmwrx.config import Config_Obj
# from mdmwrx.tools import debug


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
    c_o: Config_Obj
    aktpath: Path
    tmp_filestem: str
    mymeta: MdYamlMeta


# Böse globale Variable
lastconverted = {}


def handle_file(c_o, sourcefile, do_print=True, dryrun=False, do_force=False):
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
        mymeta.lang = c_o.lang
    
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
                
    do_convert(ConvertData(c_o, path, tmp_filestem, mymeta))  # Wenn Konvertierung nicht erfolgreich: Abbruch dort!
    
    endungen = ['_SLIDES.html', '_SLIDES.pdf', '.html', '_A4.pdf']
    for s_format in SLIDE_FORMATE.keys():
        endungen.append(f'_SLIDES_{s_format}.html')
        endungen.append(f'_SLIDES_{s_format}.pdf')
        
    for endung in endungen:

        # uralte immer entfernen (sollten anderweitig bereits entfernt worden sein)
        (path / f'_mdm_old_{sourcefile.stem}{endung}').unlink(missing_ok=True)

        # alte immer umbenennen, auch wenn sie nicht ersetzt werden (dann müssen sie trotzdem weg)
        try:
            (path / f'{sourcefile.stem}{endung}').rename(path / f'_mdm_old_{sourcefile.stem}{endung}')
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
        make_sitemap_file(c_o, path)
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
                make_sitemap_file(c_o, path)
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
                print("\nPause abgebrochen. Kein Problem, lösche trotzdem schnell mdm_old-Dateien.")
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
                print("\nPause abgebrochen. Kein Problem, lösche trotzdem schnell mdm_old-Dateien.")
                alte_Dateien_entfernen(startpath, True, do_recursive)
                print("Fertig & beendet (wegen KeyboardInterrupt)")
                exit()


def alte_Dateien_entfernen(path, force_all=False, do_recursive=False):
    for oldfile in path.iterdir():
        if oldfile.is_file():
            if oldfile.stem.startswith("_mdm_aged_"):
                print(f"    'remove' vor-vorherige Version ({oldfile.name}).")
                oldfile.unlink(missing_ok=True)
        elif do_recursive and oldfile.is_dir():
            alte_Dateien_entfernen(oldfile, force_all, do_recursive)
    for oldfile in path.iterdir():
        if oldfile.is_file():
            if oldfile.stem.startswith("_mdm_old_"):
                if force_all:
                    print(f"    'remove' vorherige Version ({oldfile.name}).")
                    oldfile.unlink(missing_ok=True)
                else:
                    print(f"    'aging'  vorherige Version ({oldfile.name}).")
                    try:
                        oldfile.rename(path / f'_mdm_aged_{oldfile.name[9:]}')
                    except FileNotFoundError:
                        pass
            

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

    print(yaml_dict)    # nur für debugging
    if yaml_dict:
        gen_slides_value = yaml_dict.get("m²_generate_slides")
        if gen_slides_value and str(gen_slides_value)[0].lower() in ("t", "y", "j", "1", "k"):
            mymeta.gen_slides_flag = True
            if str(gen_slides_value)[0].lower() == "k":
                mymeta.keep_slides_html_flag = True
        
        mymeta.lang = yaml_dict.get("lang")
        mymeta.title = yaml_dict.get("title")
        # print("YAML-title: ", mymeta.title)
        mymeta.suppress_pdf_flag = yaml_dict.get("m²_suppress_pdf", False)
        includes = yaml_dict.get("m²_include_after")
        if isinstance(includes, str):
            includes = [includes]
        if not isinstance(includes, list):
            includes = []
        
        # Nun eine Liste einzufügender Style-Schnipsel-Dateien
        i_s = yaml_dict.get("m²_include_style")
        mymeta.inc_style_list = get_yaml_value_2_list(i_s)
        
        # Nun eine Liste der zu erzeugenden Slide-Formate mit mindestens einem Wert drin.
        s_f = yaml_dict.get("m²_slide_format")
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
