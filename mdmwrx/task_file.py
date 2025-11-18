"""task_file.py
Erhält die konkrete Aufgaben handle_file von
 mdmachine oder von handle_dir.
"""

# Batteries included
import uuid
import shutil
import time
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

# MDMWRX
from mdmwrx.pre_proc import do_pre_proc
from mdmwrx.yamlread import get_yaml_dict_from_md
from mdmwrx.converter import do_convert, SLIDE_FORMATE
from mdmwrx.config import Config_Obj, relpath_2_root
# from mdmwrx.tools import debug


@dataclass
class MdYamlMeta:  
    """ Diese reine Daten-Klasse enthält ausgewählte eingelesene YAML-Variablen EINER md-Datei.
        Ggf. sind die Variablen-Werte 
        - wenn sie in der md-Datei NICHT gesetzt wurden - 
        von der mdm_root-Datei festgelegt worden.
    """
    title: str = ""
    force_title: bool = False
    gen_slides_flag: bool = False
    keep_slides_html_flag: bool = False
    suppress_pdf_flag: bool = False
    lang: str = ""
    relpath2r: str = ""
       
    
@dataclass
class ConvertData:
    """ Diese reine Daten-Klasse vereint notwendige Daten, davon zwei weitere Datenklassen, 
        welche für die Konvertierung von Dateien nötig sind.
    """
    c_o: Config_Obj
    aktpath: Path
    tmp_filestem: str
    mymeta: MdYamlMeta


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
        lasttime = c_o.lastconverted.get(sourcefile.absolute(), 0)
        if lasttime and lasttime < sourcefile.stat().st_mtime:
            flag_do_convert = True
            print("")
            print(f'src>: {sourcefile.name: <38} ist neuer als '
                  'der Beginn der letzten Konvertierung. Konvertiere sofort!')
        elif htmlfile.stat().st_mtime < sourcefile.stat().st_mtime + 2:
            print(f'>trg: {htmlfile.name: <38} älter als Quelldatei {sourcefile.name}.')
            while sourcefile.stat().st_mtime + 2 > int(time.time()):
                time.sleep(1)
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
    mymeta, includes = get_meta_from_mdyaml(c_o, sourcefile)
    
    tmp_filestem = "_mdmtemp_" + uuid.uuid4().hex
    tmp_preproc_file = path / f'{tmp_filestem}_preproc.md'
    tmp_concat_file = path / f'{tmp_filestem}_concat.md'
    # print("vermerke ", sourcefile.absolute(), time.time())
    c_o.lastconverted[sourcefile.absolute()] = time.time()
    
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


def alte_Dateien_entfernen(path, force_all=False, do_recursive=False, remove_temps=False):
    delled_old=False
    temp_counter = 0
    for oldfile in path.iterdir():
        if oldfile.is_file():
            if oldfile.stem.startswith("_mdm_aged_"):
                print(f"    'remove' vor-vorherige Version ({oldfile.name}).")
                oldfile.unlink(missing_ok=True)
                delled_old=True
        elif do_recursive and oldfile.is_dir():
            alte_Dateien_entfernen(oldfile, force_all, do_recursive)
    for oldfile in path.iterdir():
        if oldfile.is_file():
            if oldfile.stem.startswith("_mdm_old_"):
                if force_all:
                    print(f"    'remove' vorherige Version ({oldfile.name}).")
                    oldfile.unlink(missing_ok=True)
                else:
                    if delled_old:
                        print("    -> Pause zwischen remove und aging...")
                        time.sleep(3)   # Feigheit vor der Cloudsynchronisation, aber nur einmal
                        delled_old = False
                    print(f"    'aging'  vorherige Version ({oldfile.name}).")
                    try:
                        oldfile.rename(path / f'_mdm_aged_{oldfile.name[9:]}')
                    except FileNotFoundError:
                        pass
            elif remove_temps and oldfile.stem.startswith("_mdmtemp_"):
                oldfile.unlink(missing_ok=True)
                temp_counter += 1
    if temp_counter:
        print(f'{temp_counter} temporäre Dateien gelöscht.')


def get_meta_from_mdyaml(c_o, mdfile):
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

    yaml_dict = get_yaml_dict_from_md(mdfile)  # existiert immer, aber ggf. leer, 
    includes = []

    mymeta.relpath2r = relpath_2_root(mdfile.parent)
    # print(f'Weg zu root: {relpath2r}')

    # print(yaml_dict)    # nur für debugging
    # Merke: default bei .get() wird nur genommen, wenn gar kein Wert gesetzt ist!
    mymeta.gen_slides_flag = yaml_dict.get_bool("m²_generate_slides", c_o.flag_gen_slides, accept_char_as_true="kK")
    if mymeta.gen_slides_flag and str(yaml_dict.get("m²_generate_slides")).lower().startswith("k"):
        mymeta.keep_slides_html_flag = True

    mymeta.lang = yaml_dict.get("lang", c_o.lang)
    mymeta.title = yaml_dict.get("title")
    # print("YAML-title: ", mymeta.title)
    mymeta.suppress_pdf_flag = yaml_dict.get("m²_suppress_pdf", c_o.flag_sup_pdf)   
    
    includes = yaml_dict.get_list("m²_include_after")
    
    # Nun eine Liste einzufügender Style-Schnipsel-Dateien
    mymeta.inc_style_list = yaml_dict.get_list_lowered("m²_include_style")
    
    # Nun eine Liste der zu erzeugenden Slide-Formate mit mindestens einem Wert drin.
    mymeta.slide_format_list = yaml_dict.get_list_lowered("m²_slide_format", ["a5"])
        
    if not mymeta.title:
        mymeta.title = mdfile.stem
        mymeta.force_title = True

    return mymeta, includes
