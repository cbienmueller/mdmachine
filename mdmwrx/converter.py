# Batteries
import os
import subprocess

from pathlib import Path

# Gemischte Gefühle für mypy & typing
import typing
if typing.TYPE_CHECKING:
    from mdmwrx.task_file import Convert_Data

# MDMWRX
from mdmwrx.tools import debug


""" führt die eigentlich md->html->pdf - Konvertierung durch. Ggf. doppelt, wenn auch Slides gewünscht sind.
"""

CONVERT_VERBOSE = False

# SLIDE_... und INCLUDE_CSS werden unterschieden, da SLIDE... zu verschiedenen Dateien führt - INC ändert nur den Inhalt.
SLIDE_FORMATE = {
    "gen8": 'css_gen8_slides.txt',
    "beamer": 'css_beamer_slides.txt',
    "fhd": 'css_fhd_slides.txt',
    "fhd2": 'css_fhd2_slides.txt',
    'a5': ''}

SLIDE_FORMAT_DESC = {
    "gen8": 'iPad Gen. 8',
    "beamer": 'Beamer 1280x800',
    "fhd": 'Full-HD',
    "fhd2": 'Full-HD+X',
    'a5': 'Din-A5 quer, iPad Air 5'}

INCLUDE_STYLE = {
    "schule": 'schule_style.txt', 
    "orange": 'orange_style.txt', 
}

DYN_HEADER = """<!-- Dyn_header.txt: Wird je nach Konfig. erstellt, benutzt, gelöscht -->
<link
    rel="preload"
    as="font"
    crossorigin="anonymous"
    href="{}"
    type="font/woff2"
>

<link rel="Stylesheet" type="text/css" href="{}">
<link rel="Stylesheet" type="text/css" href="{}">

"""


def dbg(ort: str, variable: str, wert: str, comment: str = "") -> None:
    if CONVERT_VERBOSE:
        print(f'''In {ort}: {
              variable} = {
              wert} {
              "" if not comment else f'({comment})'}''')
  
    
def filtererrors(fehlerblock: str) -> str:
    ignore_patterns = [':INFO:', ':WARNING:', 'system_bus_socket', 'Fontconfig error:', 
                       'bytes written', ':ERROR:bus.', ':ERROR:kwallet', 'cannot touch', 
                       'org.freedesktop.DBus', 'org.freedesktop.portal.GlobalShortcuts.Activated',
                       'PHONE_REGISTRATION_ERROR', 'DEPRECATED_ENDPOINT', 'mcs_client']
    ausgabe = []
    for zeile in fehlerblock.splitlines():
        auslassen = False
        for pattern in ignore_patterns:
            if pattern in zeile:
                auslassen = True
        if not auslassen:
            ausgabe.append(zeile)
    return '\n'.join(ausgabe)


def do_convert(co_da: 'Convert_Data'): 
    erfolg = convert2html(co_da)
    if co_da.mymeta.suppress_pdf_flag:
        return 
    if not co_da.c_o.browser_engine:
        print("Kein Browser gefunden, daher keine PDF-Generierung!")
    else:
        if erfolg:
            erfolg = convert2A4pdf(co_da)
        if erfolg and co_da.mymeta.gen_slides_flag:
            erfolg = convert2slides(co_da)

    if not erfolg:
        if not CONVERT_VERBOSE:
            # Aufräumen...
            for tf in co_da.aktpath.glob(f'{co_da.tmp_filestem}*'):
                try:
                    tf.unlink()
                except Exception:
                    pass
    
        print("Abbruch wegen Konvertierungsfehler")
        exit()
        
    
def call_my_script(co_da: 'Convert_Data'):
    """Ruft das im Verzeichnis befindliche _mdmtemp..._todo.sh DIREKT auf
    """
    
    # print("  ToDo-Skript startet")
    kommando = [
        'bash',
        f'{co_da.tmp_filestem}_todo.sh']
        
    out, err = b"", b""
    prev_cwd = Path.cwd()
    os.chdir(co_da.aktpath)
    try:
        p = subprocess.Popen(" ".join(kommando), shell=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE) 
        try:
            out, err = p.communicate(timeout=31)   # 31 Sekunden Timeout sollten reichen...
        except subprocess.TimeoutExpired:
            p.kill()
            print("ToDo-skript nicht schnell genug fertig!")
            # out, err = p2.communicate()
        except Exception as e:
            print("Unbekannter Fehler:")
            print(e)
    finally:
        os.chdir(prev_cwd)
    
    # print('  ToDo-Skript beendet')
    if out:
        print("\nstdout:\n" + out.decode('utf-8'))
    if err:
        errfiltered = filtererrors(err.decode('utf-8'))
    else:
        errfiltered = ""
    if errfiltered:
        print("\nstderr:\n" + errfiltered)
    

def get_inc_txt_filename(co_da: 'Convert_Data', inc_name: str, inc_type: str) -> str:
    """ Schaut ob eine geeignete Datei im Medienverzeichnis von mdmachine zu finden ist.
    """
    save_name = "".join(x for x in inc_name if (x.isalnum() or x in "_-"))
    for prefix in ["mdm", "user"]:
        realpath = co_da.c_o.medien_path / f'{prefix}_{save_name}_{inc_type}.txt'
        if realpath.is_file():
            return (f'{prefix}_{save_name}_{inc_type}.txt')
    return ""


def convert2html(co_da: 'Convert_Data') -> bool:
    """Konvertiere eine von pre_proc generierte Markdowndatei in ggf. mehrere HTML-Dateien.
        - mymeta.gen_slides entscheidet, ob überhaupt weitere HTML-Dateien für SLIDES erzeugt werden
        - mymeta.slide_width_list enthält eine Liste der zu erzeugenden SLIDE-Formate (auch bei einem eizelnen Wert in YAML)
    """
    print(f'''Konvertiere '{co_da.mymeta.title}' nun in HTML {", auch für Slides" if co_da.mymeta.gen_slides_flag else ""}''')

    medienurl = str(co_da.c_o.medien_path)
    
    # Es werden Styles gesucht, die entweder immer, nur in Slides oder nur in Nicht-Slides eingefügt werden 
    style_files_list = []
    style_slides_files_list = []
    style_no_slides_files_list = []
    style_list = ['master']
    if co_da.c_o.inc_style_list:
        style_list += co_da.c_o.inc_style_list 
    if co_da.mymeta.inc_style_list:
        style_list += co_da.mymeta.inc_style_list
    for inc_style in style_list:
        gibt_slidestyle_flag = False
        # braucht und gibt es einen user_<bla>_style_slides.txt?
        if co_da.mymeta.gen_slides_flag:
            inc_style_filename = get_inc_txt_filename(co_da, inc_style, 'style_slides')
            debug(co_da.c_o, "inc_style_slides_filename", inc_style_filename)
            if inc_style_filename:
                style_slides_files_list += ['-A', f'{medienurl}/{inc_style_filename}']
                gibt_slidestyle_flag = True
        
        # gibt es einen user_<bla>_style.txt?
        inc_style_filename = get_inc_txt_filename(co_da, inc_style, 'style')
        debug(co_da.c_o, "inc_style_filename", inc_style_filename)
        if inc_style_filename:
            if gibt_slidestyle_flag:
                # Wird also nur für nicht-Slides verwendet
                style_no_slides_files_list += ['-A', f'{medienurl}/{inc_style_filename}']
            else:
                # Wird für alle Dateien verwendet
                style_files_list += ['-A', f'{medienurl}/{inc_style_filename}']
        elif not gibt_slidestyle_flag:
            print(f'Fehler: der includierte Style {inc_style} wurde als Datei {inc_style_filename} nicht gefunden.')
    # Anfang der Liste der Parameter um HTML zu erzeugen
    html_todo_base = [                                      
        'pandoc', 
        '-s']                                               # pandoc soll stand-alone erzeugen (mit header, body usw.)
        
    # Titel wurde aus dem Dateinamen errechnet wenn kein Titel im Source-md enthalten ist. Dann hier einsetzen!
    if co_da.mymeta.force_title:
        html_todo_base += [
            '--metadata', f'pagetitle="{co_da.mymeta.title}"']  

    # Einzubindende CSS-Dateien sind nicht mehr hart verdrahtet, sondern werden ggf. mdm_root.yaml entnommen
    with open((co_da.aktpath / f'{co_da.tmp_filestem}_header.txt'), 'w') as f:
        f.write(DYN_HEADER.format(co_da.c_o.mainfont,
                                  co_da.c_o.cssfile_main,
                                  co_da.c_o.cssfile_md))
        for cssitem in co_da.c_o.inc_css_list:
            f.write(f'<link rel="Stylesheet" type="text/css" href="{co_da.mymeta.relpath2r}/{cssitem}">\n')
        if co_da.c_o.inc_main_css:
            if co_da.c_o.inc_main_css.lower().startswith('https://') or \
               co_da.c_o.inc_main_css.lower().startswith('http://'):
                f.write(f'<link rel="Stylesheet" type="text/css" href="{co_da.c_o.inc_main_css}">\n')
            else:   
                f.write(f'<link rel="Stylesheet" type="text/css" href="{co_da.mymeta.relpath2r}/{co_da.c_o.inc_main_css}">\n')
        
    html_todo_base += [    
        '-V', f'lang="{co_da.mymeta.lang}"',                   # kommt aus YAML-Einträgen
        '--toc', '--toc-depth=2',                           # Regeln für Inhaltsverzeichnis
        '-M', 'document-css=false',                         # unterdrücke CSS von pandoc
        '-H', f'{co_da.tmp_filestem}_header.txt',              # mit den generierten CSS-Datei-URLs usw.
        '-H', f'{medienurl}/mdm_master_header.txt',         # füge script in den header ein
        f'--template={medienurl}/m2_template.html',         # nutze ein modifiziertes Template
        '--syntax-highlighting', f'{medienurl}/solarizeddark.theme',  # wähle universellen Syntax-Highlighting-Stil
        '--mathjax=https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'] + \
        style_files_list                                    # include-Styles für alle Ausgabetypen
    
    html_todo = html_todo_base + [
        '-o', f'{co_da.tmp_filestem}.html',                   # Standard-Zieldatei
        f'{co_da.tmp_filestem}_preproc.md'] + \
        style_no_slides_files_list                      # include-Styles für alle Ausgabetypen AUSSER Slides

    # '-A', f'{medienurl}/mdm_footer.txt',                     # füge HTML + Script am Ende des Bodys ein    
    
    slides_todo = []                                    # Liste der Parameter um HTML-Slides zu erzeugen
    if co_da.mymeta.gen_slides_flag and co_da.mymeta.slide_format_list:
        for s_format in co_da.mymeta.slide_format_list:
            slides_todo += html_todo_base.copy()              
            slide_format_filename = SLIDE_FORMATE.get(s_format)
            # print ("slide_format_filename = ", slide_format_filename)
            if slide_format_filename:
                additional_stylefile = [
                    '-A', f'{medienurl}/{slide_format_filename}'
                ]
                s_format_ext = "_" + s_format  # für Dateinamen
            else:
                additional_stylefile = []
                s_format_ext = "_a5"
                
            slides_todo += [
                '-o', f'{co_da.tmp_filestem}_SLIDES{s_format_ext}.html']        # andere Zieldatei
            
            slides_todo += style_slides_files_list              # # include-Styles spezifisch für alle Slides
            slides_todo += additional_stylefile
            slides_todo += [
                f'{co_da.tmp_filestem}_preproc.md',                # temporäre Eingabedatei nach Präprozessing
                '\n'] 

            # '-A', f'{medienurl}/mdm_footer_slides.txt',     # füge HTML am Ende des Bodys ein

    with open((co_da.aktpath / f'{co_da.tmp_filestem}_todo.sh'), 'w') as f:
        f.write('# Shellskript, das direkt ausgeführt wird\n')
        f.write('echo "    Starting: convert to html"\n')
        f.write(" ".join(html_todo))
        f.write("\n")
        f.write(" ".join(slides_todo))
        f.write("\n")
        f.write('echo "    Finished: convert to HTML"\n')
            
    call_my_script(co_da)
        
    if not (co_da.aktpath / f'{co_da.tmp_filestem}.html').exists():
        print(f'ERROR & Abbruch! Zieldatei {co_da.tmp_filestem}.html nicht gefunden')
        return False

    return True
  

def convert2A4pdf(co_da: 'Convert_Data') -> bool:
    print(f'''Konvertiere '{co_da.mymeta.title}' nun in A4-PDF''')
    
    dotodo_go = [
        co_da.c_o.browser_engine,  
        '--no-sandbox', '--headless=true', '--disable-gpu', '--disable-search-engine-choice-screen',
        '--run-all-compositor-stages-before-draw', '--no-pdf-header-footer',
        '--no-margins', '--virtual-time-budget=400000',
        f'--print-to-pdf={co_da.tmp_filestem}_A4.pdf', f'{co_da.tmp_filestem}.html']

    dbg("convert2A4pdf", "ToDo-Skript", f'{co_da.tmp_filestem}_todo.sh')
    
    with open((co_da.aktpath / f'{co_da.tmp_filestem}_todo.sh'), 'w') as f:
        f.write('# Shellskript\n'
                'export XDG_CONFIG_HOME=/tmp/m²_config\n'
                'export XDG_CACHE_HOME=/tmp/m²_cache\n')
        f.write('echo "    Starting: convert to A4.pdf"\n')
        f.write(" ".join(dotodo_go))
        f.write("\n")
        f.write('echo "    Finished: convert to A4.pdf"\n')
        f.write("\n")

    call_my_script(co_da)
    
    if not (co_da.aktpath / f'{co_da.tmp_filestem}_A4.pdf').exists():
        print(f'ERROR & Abbruch! Zieldatei {co_da.tmp_filestem}_A4.pdf nicht gefunden')
        return False

    return True


def convert2slides(co_da: 'Convert_Data') -> bool:
    if co_da.mymeta.slide_format_list:
        for s_format in co_da.mymeta.slide_format_list:
            print(f'''Konvertiere '{co_da.mymeta.title}' nun in {s_format}-PDF''')

            slide_format_filename = SLIDE_FORMATE.get(s_format)
            if slide_format_filename:
                s_format_ext = "_" + s_format  # für Dateinamen
            else:
                s_format_ext = "_a5"
                
            slides_html_filename = f'{co_da.tmp_filestem}_SLIDES{s_format_ext}.html'
            slides_pdf_filename = f'{co_da.tmp_filestem}_SLIDES{s_format_ext}.pdf'
            
            slides_todo = [
                co_da.c_o.browser_engine, 
                '--no-sandbox', '--headless', '--disable-gpu', '--disable-search-engine-choice-screen',
                '--run-all-compositor-stages-before-draw', '--print-to-pdf-no-header',
                '--no-margins', '--virtual-time-budget=400000',
                f'--print-to-pdf={slides_pdf_filename}', slides_html_filename]
            
            with open((co_da.aktpath / f'{co_da.tmp_filestem}_todo.sh'), 'w') as f:
                f.write('# Shellskript\n'
                        'export XDG_CONFIG_HOME=/tmp/m²_config\n'
                        'export XDG_CACHE_HOME=/tmp/m²_cache\n')
                f.write(f'echo "    Starting: convert to SLIDE{s_format_ext}.pdf"\n')
                f.write(" ".join(slides_todo))
                f.write("\n")
                f.write(f'echo "    Finished: convert to SLIDE{s_format_ext}.pdf"\n')
                
            call_my_script(co_da)
            
            if not (co_da.aktpath / slides_pdf_filename).exists():
                print(f'ERROR & Abbruch! Zieldatei {slides_pdf_filename} nicht gefunden')
                return False

    return True
