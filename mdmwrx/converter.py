import os
import subprocess

from pathlib import Path

""" führt die eigentlich md->html->pdf - Konvertierung durch. Ggf. doppelt, wenn auch Slides gewünscht sind.
    Dabei wird so oder so nur ein Docker-Aufruf gemacht.
"""

browserengine = 'google-chrome'
# browserengine = 'brave-browser'

conv_verbose = True


# SLIDE_... und INCLUDE_CSS werden unterschieden, da SLIDE... zu verschiedenen Dateien führt - INC ändert nur den Inhalt.
SLIDE_FORMATE = {
    "gen8": '/opt/medien/css_gen8_slides.txt',
    "beamer": '/opt/medien/css_beamer_slides.txt',
    "fhd": '/opt/medien/css_fhd_slides.txt',
    'a5': ''}

SLIDE_FORMAT_DESC = {
    "gen8": 'iPad Gen. 8',
    "beamer": 'Beamer 1280x800',
    "fhd": 'Full-HD',
    'a5': 'Din-A5 quer, iPad Air 5'}

INCLUDE_STYLE = {
    "schule": '/opt/medien/schule_style.txt', 
    "orange": '/opt/medien/orange_style.txt', 
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


def dbg(ort, variable, wert, comment=""):
    if conv_verbose:
        print(f'''In {ort}: {
              variable} = {
              wert} {
              "" if not comment else f'({comment})'}''')
  
    
def filtererrors(fehlerblock):
    ignore_patterns = [':INFO:', ':WARNING:', 'system_bus_socket', 'Fontconfig error:', 
                       'bytes written', ':ERROR:bus.', ':ERROR:kwallet', 'cannot touch', 
                       'org.freedesktop.DBus', 'org.freedesktop.portal.GlobalShortcuts.Activated']
    ausgabe = []
    for zeile in fehlerblock.split('\n'):
        auslassen = False
        for pattern in ignore_patterns:
            if pattern in zeile:
                auslassen = True
        if not auslassen:
            ausgabe.append(zeile)
    return '\n'.join(ausgabe)


def do_convert(cd):  # cd: ConvertData
    erfolg = convert2html(cd)
    if cd.mymeta.suppress_pdf_flag:
        return 
    if erfolg:
        erfolg = convert2A4pdf(cd)
    if erfolg and cd.mymeta.gen_slides_flag:
        erfolg = convert2slides(cd)

    if not erfolg:
        if not conv_verbose:
            # Aufräumen...
            for tf in cd.aktpath.glob(f'{cd.tmp_filestem}*'):
                try:
                    tf.unlink()
                except Exception:
                    pass
    
        print("Abbruch wegen Konvertierungsfehler")
        exit()
        
        
def call_my_docker(cd):
    """Ruft 'mein' Dockerimage auf und startet dort das im Verzeichnis befindliche _mdmtemp..._todo.sh
    """
    mount_path = f'--mount type=bind,source={cd.aktpath},target=/data'
    mount_medien = f' --mount type=bind,source={cd.c_o.medien_path},target=/opt/medien'
    mount_tmp = '--mount type=bind,source=/tmp/mdmachine,target=/tmp'
    uid = os.geteuid()
    gid = os.getegid()
    errfiltered = ''
    if not cd.mymeta.lang:
        cd.mymeta.lang = 'de'
    kommando = [
        'docker', 'run', '--entrypoint', 'bash', '--rm', 
        mount_path,
        mount_medien,
        mount_tmp, 
        '--user', f'{uid}:{gid}', 
        'pandoc/core:3.7-ubuntu',          # war 'biec/pandocker',                               # mein docker image
        f'{cd.tmp_filestem}_todo.sh']

    print("Starte Docker...")
    p = subprocess.Popen(" ".join(kommando), shell=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE) 
    out, err = "", ""
    try:
        out, err = p.communicate(timeout=31)   # 31 Sekunden Timeout sollten jetzt in Docker reichen...
    except subprocess.TimeoutExpired:
        p.kill()
        print("pandoc@docker nicht schnell genug fertig!")
        # out, err = p2.communicate()
    except Exception as e:
        print("Unbekannter Fehler:")
        print(e)

    print("...beendet")
    print('docker (pandoc) fertig')
    if out:
        print("\nstdout:\n" + out.decode('utf-8'))
    if err:
        errfiltered = filtererrors(err.decode('utf-8'))
    if errfiltered:
        print("\nstderr:\n" + errfiltered)
    
    
def call_my_script(cd):
    """Ruft das im Verzeichnis befindliche _mdmtemp..._todo.sh DIREKT auf
    """
    
    print("Starte ToDo-Skript...")
    kommando = [
        'bash',
        f'{cd.tmp_filestem}_todo.sh']
        
    out, err = "", ""
    prev_cwd = Path.cwd()
    os.chdir(cd.aktpath)
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
    
    print("...beendet")
    print('ToDo-Skript beendet')
    if out:
        print("\nstdout:\n" + out.decode('utf-8'))
    if err:
        errfiltered = filtererrors(err.decode('utf-8'))
    if errfiltered:
        print("\nstderr:\n" + errfiltered)
    
    
def convert2html(cd):
    """Konvertiere eine von pre_proc generierte Markdowndatei in ggf. mehrere HTML-Dateien.
        - mymeta.gen_slides entscheidet, ob überhaupt weitere HTML-Dateien für SLIDES erzeugt werden
        - mymeta.slide_width_list enthält eine Liste der zu erzeugenden SLIDE-Formate (auch bei einem eizelnen Wert in YAML)
    """
    print(f'''Konvertiere '{cd.mymeta.title}' nun in HTML {", auch für Slides" if cd.mymeta.gen_slides_flag else ""}''')

    inc_liste = []
    if cd.mymeta.inc_style_list:
        for inc_style in cd.mymeta.inc_style_list:
            inc_style_filename = INCLUDE_STYLE.get(inc_style)
            print("inc_style_filename = ", inc_style_filename)
            if inc_style_filename:
                inc_liste += ['-A', inc_style_filename]
    
    html_todo_base = [                                      # Anfang der Liste der Parameter um HTML zu erzeugen
        'pandoc', 
        '-s']                                               # pandoc soll stand-alone erzeugen (mit header, body usw.)
        
    if cd.mymeta.force_title:
        html_todo_base += [
            '--metadata', f'pagetitle="{cd.mymeta.title}"']  # Titel aus dem Dateinamen wenn nicht im Source-md enthalten.

    with open((cd.aktpath / f'{cd.tmp_filestem}_header.txt'), 'w') as f:
        f.write(DYN_HEADER.format(cd.c_o.mainfont,
                                  cd.c_o.cssfile_main,
                                  cd.c_o.cssfile_md))
        
    html_todo_base += [    
        '-V', f'lang="{cd.mymeta.lang}"',                   # kommt aus YAML-Einträgen
        '--toc', '--toc-depth=2',                           # Regeln für Inhaltsverzeichnis
        '-M', 'document-css=false',                         # unterdrücke CSS von pandoc
        '-H', f'{cd.tmp_filestem}_header.txt',              # mit ggf. anderen CSS-Datei-URLs usw.
        '-H', '/opt/medien/mdm_header.txt',                 # füge script und css-Links in den header ein
        '--highlight-style', 'pygments',                    # wähle einen besser lesbaren Syntax-Highlighting-Stil
        '--mathjax=https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'] + \
        inc_liste
    
    html_todo = html_todo_base + [
        '-o', f'{cd.tmp_filestem}.html',                   # Standard-Zieldatei
        '-A', '/opt/medien/mdm_footer.txt',                     # füge HTML + Script am Ende des Bodys ein
        f'{cd.tmp_filestem}_preproc.md']                   # temporäre Eingabedatei nach Präprozessing
    
    slides_todo = []                                    # Liste der Parameter um HTML-Slides zu erzeugen
    if cd.mymeta.gen_slides_flag:
        for s_format in cd.mymeta.slide_format_list:
            slides_todo += html_todo_base.copy()              
            slide_format_filename = SLIDE_FORMATE.get(s_format)
            # print ("slide_format_filename = ", slide_format_filename)
            if slide_format_filename:
                additional_stylefile = [
                    '-A', slide_format_filename
                ]
                s_format_ext = "_" + s_format  # für Dateinamen
            else:
                additional_stylefile = []
                s_format_ext = "_a5"
                
            slides_todo += [
                '-o', f'{cd.tmp_filestem}_SLIDES{s_format_ext}.html',        # andere Zieldatei
                '-A', '/opt/medien/mdm_css_slides.txt']             # füge am Ende noch styles für Präsentationen ein
                
            slides_todo += additional_stylefile + [
                '-A', '/opt/medien/mdm_footer_slides.txt',          # füge HTML am Ende des Bodys ein
                f'{cd.tmp_filestem}_preproc.md',               # temporäre Eingabedatei nach Präprozessing
                '\n'] 

    with open((cd.aktpath / f'{cd.tmp_filestem}_todo.sh'), 'w') as f:
        f.write('# Shellskript, das im dockercontainer ausgeführt wird\n'
                'export XDG_CONFIG_HOME=/tmp/m³_config\n'
                'export XDG_CACHE_HOME=/tmp/m²_cache\n')
        f.write("echo Convert to html...\n")
        f.write(" ".join(html_todo))
        f.write("\n")
        f.write(" ".join(slides_todo))
        f.write("\n")
        f.write("echo Finished HTML\n")
            
    call_my_docker(cd) 
    
    if not (cd.aktpath / f'{cd.tmp_filestem}.html').exists():
        print(f'ERROR & Abbruch! Zieldatei {cd.tmp_filestem}.html nicht gefunden')
        return False

    return True
  

def convert2A4pdf(cd):
    print(f'Konvertiere {cd.mymeta.title} nun in A4-PDF')
    
    dotodo_go = [
        browserengine,  
        '--no-sandbox', '--headless=true', '--disable-gpu', '--disable-search-engine-choice-screen',
        '--run-all-compositor-stages-before-draw', '--no-pdf-header-footer',
        '--no-margins', '--virtual-time-budget=400000',
        f'--print-to-pdf={cd.tmp_filestem}_A4.pdf', f'{cd.tmp_filestem}.html']

    dbg("convert2A4pdf", "ToDo-Skript", f'{cd.tmp_filestem}_todo.sh')
    
    with open((cd.aktpath / f'{cd.tmp_filestem}_todo.sh'), 'w') as f:
        f.write('# Shellskript, das ggf. im dockercontainer ausgeführt wird\n'
                'export XDG_CONFIG_HOME=/tmp/m²_config\n'
                'export XDG_CACHE_HOME=/tmp/m²_cache\n')
        f.write("echo Convert to A4.pdf...\n")
        f.write(" ".join(dotodo_go))
        f.write("\n")

    # call_my_docker(cd)
    call_my_script(cd)
    
    if not (cd.aktpath / f'{cd.tmp_filestem}_A4.pdf').exists():
        print(f'ERROR & Abbruch! Zieldatei {cd.tmp_filestem}_A4.pdf nicht gefunden')
        return False

    return True


def convert2slides(cd):
        
    for s_format in cd.mymeta.slide_format_list:
        slide_format_filename = SLIDE_FORMATE.get(s_format)
        if slide_format_filename:
            s_format_ext = "_" + s_format  # für Dateinamen
        else:
            s_format_ext = "_a5"
            
        slides_html_filename = f'{cd.tmp_filestem}_SLIDES{s_format_ext}.html'
        slides_pdf_filename = f'{cd.tmp_filestem}_SLIDES{s_format_ext}.pdf'
        
        slides_todo = [
            browserengine, 
            '--no-sandbox', '--headless', '--disable-gpu', '--disable-search-engine-choice-screen',
            '--run-all-compositor-stages-before-draw', '--print-to-pdf-no-header',
            '--no-margins', '--virtual-time-budget=400000',
            f'--print-to-pdf={slides_pdf_filename}', slides_html_filename]
        
        with open((cd.aktpath / f'{cd.tmp_filestem}_todo.sh'), 'w') as f:
            f.write('# Shellskript, das ggf. im dockercontainer ausgeführt wird\n'
                    'export XDG_CONFIG_HOME=/tmp/m²_config\n'
                    'export XDG_CACHE_HOME=/tmp/m²_cache\n')
            f.write(f"echo Convert to SLIDE{s_format_ext}.pdf...\n")
            f.write(" ".join(slides_todo))
            f.write("\n")
            f.write("echo Finished a SLIDE.pdf\n")
            
        call_my_script(cd)
        
        if not (cd.aktpath / slides_pdf_filename).exists():
            print(f'ERROR & Abbruch! Zieldatei {slides_pdf_filename} nicht gefunden')
            return False

    return True
