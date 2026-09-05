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
# from hashlib import file_digest

# Gemischte Gefühle für mypy & typing
import typing
from typing import Optional
if typing.TYPE_CHECKING:
    import mdmwrx.config

# MDMWRX
from mdmwrx.pre_proc import do_pre_proc
from mdmwrx.yamlread import get_yaml_dict_from_md
from mdmwrx.converter import do_convert, SLIDE_FORMATE
from mdmwrx.config import Config_Obj, relpath_2_root
from mdmwrx.tools import alte_Dateien_vorhanden   # debug
from mdmwrx.task_sidefiles import make_sidebar_file, overwrite_if_changed


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
    inc_style_list: Optional[list[str]] = None
    slide_format_list: Optional[list[str]] = None
    includes_list: Optional[list[str]] = None
    force_pdf_stem: Optional[str] = ""
    force_ignore_pdfs: Optional[bool] = False
    generate_chapter_file: Optional[bool] = False
    is_generated: Optional[bool] = False
    keywords: Optional[str] = ""
    description: Optional[str] = ""
    abstract: Optional[str] = ""


@dataclass
class Convert_Data:
    """ Diese reine Daten-Klasse vereint notwendige Daten, davon zwei weitere Datenklassen, 
        welche für die Konvertierung von Dateien nötig sind.
    """
    c_o: Config_Obj
    aktpath: Path
    tmp_filestem: str
    mymeta: MdYamlMeta


def handle_file(c_o: 'mdmwrx.config.Config_Obj',
                sourcefile: Path,
                do_print: bool = True,
                dryrun: bool = False,
                do_force: bool = False,
                ignore_sidebar: bool = False
                ) -> tuple[bool, int]:
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

        else:
            if do_print:
                print(f'''>trg: {htmlfile.name: <38} mtime: {
                    datetime.fromtimestamp(htmlfile.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')} (keine Konv. nötig)''')
            # Nun inspizieren wir die Liste der Include-Dateien...
            source_mdyamlmeta = get_meta_from_mdyaml(c_o, sourcefile)
            if source_mdyamlmeta.includes_list is not None:
                flag_include_test_info_unprinted = True
                for incname in source_mdyamlmeta.includes_list:
                    incfile = path / incname
                    if incfile.exists():
                        if flag_include_test_info_unprinted and do_print:
                            print("Includedateien checken...")
                            flag_include_test_info_unprinted = False
                
                        if htmlfile.stat().st_mtime < incfile.stat().st_mtime + 2:
                            print(f'>trg: {htmlfile.name: <38} älter als Include datei {incname}.')
                            print(f'''inc>: {incname: <38} mtime: {
                                datetime.fromtimestamp(incfile.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}''')
                            flag_do_convert = True

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
    mymeta = get_meta_from_mdyaml(c_o, sourcefile)
    
    tmp_filestem = "_mdmtemp_" + uuid.uuid4().hex
    tmp_preproc_file = path / f'{tmp_filestem}_preproc.md'
    tmp_concat_file = path / f'{tmp_filestem}_concat.md'
    chapterfilecontent = []

    if mymeta.generate_chapter_file and mymeta.force_pdf_stem:
        print("Oh, generiere Chapter_File")
        chapter_file = path / (mymeta.force_pdf_stem + ".md")
        if chapter_file.exists():
            print("Chapter_File existiert schon")
            chaptermeta = get_meta_from_mdyaml(c_o, chapter_file)
            if chaptermeta.is_generated:
                print("Alles ok, ist generiert")
            else:
                print(f'Dein Fehler: Zu generierendes Chapter_File {mymeta.force_pdf_stem + ".md"}'
                      ' existiert und ist nicht als generiert gekennzeichnet!')
                mymeta.generate_chapter_file = False
    if mymeta.generate_chapter_file:
        chapterfilecontent = ['---', 
                              'm²_this_file_is_generated_and_will_be_overwritten: true',
                              'm²_ignore_pdfs: true',
                              'm²_suppress_pdf: true']
        mkneen(chapterfilecontent, 'title', mymeta.title)        
        if mkneen(chapterfilecontent, 'abstract', mymeta.abstract):
            mkneen(chapterfilecontent, 'abstract-title', '""')        
        mkneen(chapterfilecontent, 'keywords', mymeta.keywords)        
        mkneen(chapterfilecontent, 'description', mymeta.description)        
        chapterfilecontent.append('...')        
        chapterfilecontent.append('<style>\n  p { margin-left: 2em; }\n  </style>\n')
    # print("vermerke ", sourcefile.absolute(), time.time())
    c_o.lastconverted[sourcefile.absolute()] = time.time()
    
    print("Präprozessor...")
    do_pre_proc(sourcefile, tmp_preproc_file)
    
    if mymeta.includes_list:
        for incname in mymeta.includes_list:
            print(f'include-after: {incname}')
            incfile = path / incname
            if incfile.exists():
                do_pre_proc(incfile, tmp_concat_file, remove_yaml=True)
                with open(tmp_preproc_file, 'a') as prepro:
                    with open(tmp_concat_file, 'r') as concat:
                        prepro.write("\n \n \n")
                        shutil.copyfileobj(concat, prepro)
                tmp_concat_file.unlink(missing_ok=True)
                if mymeta.generate_chapter_file:
                    incmeta = get_meta_from_mdyaml(c_o, incfile)   # aus dem cache - billig...
                    chapterfilecontent.append(f'#### [{incmeta.title} ]({incfile.stem + ".html"})\n')
                    chapterfilecontent.append(f'{incmeta.abstract}\n\n')
            else:
                print(f'!!! include-file {incname} missing!!!')
                
    if mymeta.generate_chapter_file:
        overwrite_if_changed(c_o, chapter_file, "\n".join(chapterfilecontent))

    do_convert(Convert_Data(c_o, path, tmp_filestem, mymeta))  # Wenn Konvertierung nicht erfolgreich: Abbruch dort!

    if mymeta.force_ignore_pdfs:
        endungen = ['.html']    
    else:
        endungen = ['_SLIDES.html', '_SLIDES.pdf', '.html', '_A4.pdf']
        for s_format in SLIDE_FORMATE.keys():
            endungen.append(f'_SLIDES_{s_format}.html')
            endungen.append(f'_SLIDES_{s_format}.pdf')
        
    if not c_o.poll_generation:  # single shot Anwendung
        c_o.poll_generation = 100
        while alte_Dateien_vorhanden(path, c_o.poll_generation):
            c_o.poll_generation += 1

    for endung in endungen:
        use_file_stem = sourcefile.stem
        if mymeta.force_pdf_stem and endung != '.html':
            use_file_stem = mymeta.force_pdf_stem

        # uralte immer entfernen (sollten anderweitig bereits entfernt worden sein)
        (path / f'_mdm_old_{use_file_stem}{endung}').unlink(missing_ok=True)
        (path / f'_mdm_aged_{use_file_stem}{endung}').unlink(missing_ok=True)

        # alte immer umbenennen, auch wenn sie nicht ersetzt werden (dann müssen sie trotzdem weg)
        try:
            (path / f'{use_file_stem}{endung}').rename(path / f'_mdm_old-{c_o.poll_generation}_{use_file_stem}{endung}')
        except FileNotFoundError:
            pass

    # neue - müssen eigentlich existieren (und im gleichen Filesystem liegen)!
    for endung in endungen:
        use_file_stem = sourcefile.stem
        if mymeta.force_pdf_stem and endung != '.html':
            use_file_stem = mymeta.force_pdf_stem
        
        try:
            (path / f'{tmp_filestem}{endung}').rename(path / f'{use_file_stem}{endung}')
        except FileNotFoundError:
            pass

        if endung.startswith('_SLIDES') and endung.endswith('.html') and not mymeta.keep_slides_html_flag:
            (path / f'{use_file_stem}{endung}').unlink(missing_ok=True)

    # Sofort aufräumen, was nicht mehr gebraucht wird
    for tf in path.glob(f'{tmp_filestem}*'):
        try:
            tf.unlink()
        except Exception:
            pass
    if not ignore_sidebar:
        if (path / "_mdm_sidebar_.html").exists():
            make_sidebar_file(c_o, path)
    return True, 1


def get_meta_from_mdyaml(c_o: 'mdmwrx.config.Config_Obj', mdfile: Path) -> MdYamlMeta:
    """ - Liefert eine Auswahl an verwertbaren Metadaten als MdYamlMeta-Objekt
          - s.o.
        - (auch dabei: includierte md-Dateien als String-Liste)
        
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

    mymeta.relpath2r = relpath_2_root(mdfile.parent)
    # print(f'Weg zu root: {relpath2r}')

    # print(yaml_dict)    # nur für debugging
    # Merke: default bei .get() wird nur genommen, wenn gar kein Wert gesetzt ist!
    mymeta.gen_slides_flag = yaml_dict.get_bool("m²_generate_slides", c_o.flag_gen_slides, accept_char_as_true="kK")
    if mymeta.gen_slides_flag and str(yaml_dict.get("m²_generate_slides")).lower().startswith("k"):
        mymeta.keep_slides_html_flag = True

    mymeta.force_ignore_pdfs = yaml_dict.get_bool("m²_force_ignore_pdfs")   # Verhindert, dass ungenutzte PDFs gelöscht werden. 
    # Eine andere md nutzt dann den folgenen Eintrag:
    mymeta.force_pdf_stem = yaml_dict.get_str("m²_force_pdf_stem")  
    # Statt des eigenen Dateirumpfs wird dieser Wert für PDFs verwendet.
    # So kann eine md passende PDFs für eine andere generieren. Damit erscheinen beide im Inhaltsverzeichnis zusammen. Tricky

    # Soll nun eine Kapiteldatei erzeugt werden? pdf_stem wird dazu verwendet!
    mymeta.generate_chapter_file = yaml_dict.get_bool("m²_generate_chapter_file")
    if mymeta.generate_chapter_file and not mymeta.force_pdf_stem:
        print("Error: no generate_chapter without force_pdf_stem")
        mymeta.generate_chapter_file = False
    mymeta.is_generated = yaml_dict.get_bool("m²_this_file_is_generated_and_will_be_overwritten")
    
    mymeta.lang = yaml_dict.get("lang", c_o.lang)
    mymeta.title = yaml_dict.get_str("title")
    # print("YAML-title: ", mymeta.title)
    mymeta.suppress_pdf_flag = yaml_dict.get("m²_suppress_pdf", c_o.flag_sup_pdf)   
    
    mymeta.includes_list = yaml_dict.get_list("m²_include_after")
    
    # Nun eine Liste einzufügender Style-Schnipsel-Dateien
    mymeta.inc_style_list = yaml_dict.get_list_lowered("m²_include_style")
    
    # Nun eine Liste der zu erzeugenden Slide-Formate mit mindestens einem Wert drin.
    mymeta.slide_format_list = yaml_dict.get_list_lowered("m²_slide_format", ["a5"])

    mymeta.abstract = yaml_dict.get_str("abstract")        
    mymeta.keywords = yaml_dict.get_str("keywords")        
    mymeta.description = yaml_dict.get_str("description")        

    if not mymeta.title:
        mymeta.title = mdfile.stem
        mymeta.force_title = True

    return mymeta


def mkneen(lst: list[str], key: str, value: str | None) -> bool:
    """ make no empty entry"""
    if value:
        lst.append(f'{key}: {value}')
        return True
    return False

       