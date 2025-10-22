""" Erzeugt aus 
        dem Filelisting und 
        meinen Namenskonventionen
        
        eine Siedbar, mit Links zu den Dateien und Verzeichnissen.
        Fehlt: Mehr Doku zu mdm_dir.yaml und Inhalten der Unterverzeichnisse.
"""
from dataclasses import dataclass

from mdmwrx.yamlread import get_yaml_dict_from_yaml, get_yaml_dict_from_md
from mdmwrx.converter import SLIDE_FORMATE, SLIDE_FORMAT_DESC
from mdmwrx.tools import debug

SB_VERBOSE = 0

FILE_barebone = """<!DOCTYPE html>
<html lang="{}">
<head>
    <meta charset="utf-8" />
    <meta name="generator" content="mdmachine" />
    <title>{}</title>
    <link rel="Stylesheet" type="text/css" href="{}">
    <link rel="Stylesheet" type="text/css" href="{}">
</head>
"""

TIMELINE_barebone = FILE_barebone + """
<body style="width:50opx">
  <h2>Neueste Artikel</h2>
  <details open>
    <summary>
        Ein/Ausblenden
    </summary>
    <ul>
"""  
   
SIDEBAR_barebone = FILE_barebone + """
<body>
  <details open>
    <summary>Navigation</summary>
"""

SIDEBAR_sectionstart = '\t<h4>{}</h4>\n\t<ul {} style="list-style-type: none;">\n'
SIDEBAR_extern = '''\t\t<li>        <a href="{}" title="{}" target="_blank">{} </a></li>\n'''
SIDEBAR_li_bb = ['''\t\t<li class="{}"><span><em>                     <a href="{}" id="{}" title="{}" target="_parent">{}</a>
                                                                      </em></span><span>{}</span></li>\n''',
                 '''\t\t<li class="{}"><span>        <a href="{}" id="{}" title="{}" target="_parent">{}</a>
                                                                          </span><span>{}</span></li>\n''',
                 '''\t\t<li class="{}"><span><strong><a href="{}" id="{}" title="{}" target="_parent">{}</a>
                                                                  </strong></span><span>{}</span></li>\n''']
# SIDEBAR_pdf = ' &nbsp; <a href="{}" title="PDF-Version" target="_blank"><small>&#128462;</small></a>'
SIDEBAR_pdf = ' &nbsp; <a href="{}" title="PDF-Version" target="_blank"><img class="pdficon" /></a>'
SIDEBAR_slides = ' &nbsp; <a href="{}" title="PDF-SLIDES Format {}" target="_blank"><img class="slidesicon" /></a>'
SIDEBAR_sectionende = '\n\t</ul>\n'
SIDEBAR_sectionendemini = '\n\t</ul>\n'

TIMELINE_li = '\t\t<li>{} <a href="{}" id="{}" title="{}" target="_parent">{}</a> <small> in {}</small></li>\n'

SIDEBAR_fine = '''
  </details>
  <script>
    window.addEventListener(
        "message",
        (event) => {
            const callertitle = event.data;
            const linkobject = document.getElementById(callertitle);
            if (linkobject != null) {
                linkobject.style.borderBottom="2px solid var(--accent-color)";
                linkobject.style.backgroundColor="var(--bg-color)";
            }
        },
       false
    );     
    window.top.postMessage('alive', "*");
  </script>
</body></html>\n'''

TIMELINE_fine = '''
    </ul>
  </details>
</body></html>\n'''


"""const urlParams = new URLSearchParams(window.location.search);
        const callertitle = urlParams.get('ct');
        const linkobject = document.getElementById(callertitle)
        if (linkobject != null) {
            linkobject.style.borderBottom="2px solid var(--accent-color)";
            linkobject.style.backgroundColor="var(--bg-color)";
        }
"""


def make_sitemap_file(c_o, root_path):
    sm_path = root_path / 'sitemap.html'
    tl_path = root_path / '_mdm_timeline_.html'
    timeline_list = [("2024-01-01", "dummy")]
    lang = c_o.lang
    
    # ## Dateistart sitemap
    content = get_folderinfo4sitemap(root_path, "", timeline_list)  
    # wird rekursiv für jedes Unterverzeichnis aufgerufen
    # lang kommt nur vom root-mdm_dir.yaml
    
    output = SIDEBAR_barebone.format(lang, 'Sitemap', c_o.cssfile_main, c_o.cssfile_sb)
    output += content
    output += SIDEBAR_fine
    overwrite_if_changed(c_o, sm_path, output)
        
    # ## Timeline
    # timeline_list nimmt Datum und Beschreibungstext auf
    del timeline_list[0]  # dort ist nur ein Dummy
    timeline_list.sort(key=lambda tup: tup[0], reverse=True)        # sorts in place
    
    output = TIMELINE_barebone.format(lang, 'TimeLine', c_o.cssfile_main, c_o.cssfile_sb)
    for d, h in timeline_list[:16]:
        output += h
    output += TIMELINE_fine
    overwrite_if_changed(c_o, tl_path, output)


def get_side_navi(c_o, path):
    ri = get_root_info(c_o, path)
    timeline_list_dummy = [("2024-01-01", "dummy")]
    lang = ri.lang
    content = get_folderinfo4sitemap(ri.root_path, ri.updir_string, timeline_list_dummy, path)
    # wird rekursiv für jedes Unterverzeichnis aufgerufen
    # lang kommt nur vom root-mdm_dir.yaml
    # timeline_list nimmt Datum und Beschreibungstext auf
    # Enthält nur im aktpath die Dateien
    return content, lang, ri
        
        
def get_folderinfo4sitemap(root_path, relpath, timeline_list, filespath=""):
    ''' root_path ist das normalerweise das root- Verzeichnis - bei Rekursion aber ein lokales root-V..
        relpath ist der zu den Links zu addierende path, der den Ort relativ zum Verzeichnis von make_sitemap_file angibt.
        timeline_list nimmt Datei-Datum-Pärchen auf.
        filespath ist (wenn gesetzt) der einzige Pfad, bei dem Files mit aufgeführt werden. Sonst nur Verzeichnisse.
    '''
    if SB_VERBOSE:
        print("gfi4sm-> root_path: ", root_path, "rel:", relpath, "!")
    if not root_path:
        root_path = filespath  # return ""
    filename, foldertitle, yd = get_folder_filename_title_yaml(root_path)
    if not (filename and foldertitle):      # Kein Verzeichnis mit Inhalten gefunden
        return ""

    if relpath and not relpath.endswith("/"):
        relpath += "/"
    smf_output = ""
    
    if filespath and SB_VERBOSE: 
        print("filespath, root_path:", filespath, root_path)

    if not filespath or root_path == filespath:
        all_files = True
    else:
        all_files = False
    l_section, _, _, _ = get_files_section(root_path, relpath, timeline_list, all_files)
    smf_output += l_section

    smf_sub_output = ""
    for subdir in root_path.iterdir():
        if subdir.is_dir():
            if SB_VERBOSE:
                print("sitemap: recurse into -> " + subdir.name)
            content = get_folderinfo4sitemap(subdir, relpath + subdir.name, timeline_list, filespath)
            smf_sub_output += content
    if smf_sub_output:
        smf_output += SIDEBAR_sectionstart.format("", "")
        smf_output += smf_sub_output
        smf_output += SIDEBAR_sectionende
    if SB_VERBOSE > 1:
        print(f"smf_output:{smf_output}")
    return smf_output
    

def make_sidebar_file(c_o, path, do_recursive=False):
    file_path = path / '_mdm_sidebar_.html'
    output = ""

    navi_content, lang, ri = get_side_navi(c_o, path)

    output += SIDEBAR_barebone.format(lang, 'Navigation', c_o.cssfile_main, c_o.cssfile_sb)
    output += navi_content               # komplette Navigation
    output += '\t<hr>\n'                 # Trennlinie
    
    link_section, l_anzahl = get_links_section(path)
    
    output += link_section

    if (link_section and ri.fixlink_section):
        output += '\t<hr>\n'                 # Trennlinie

    output += ri.fixlink_section

    output += SIDEBAR_fine

    overwrite_if_changed(c_o, file_path, output)
        
    if do_recursive:
        for subdir in path.iterdir():
            if subdir.is_dir():
                debug(c_o, "recurse sidebar -> " + subdir.name)
                make_sidebar_file(c_o, subdir, do_recursive)


def overwrite_if_changed(c_o, file_path, content):
    """ Einige Dateien werden regelmäßig neu erstellt.
        Wenn sie sich dabei inhaltlich nicht ändern, so erzeugt das unnötige 
            Schreiblast auf dem Speichermedium und setzt auch das 
            Änderungsdatum unnötig neu, was sich wiederum auf Uploads usw. auswirkt.
        Die bestehende Datei wird daher eingelesen (meist aus dem Cache), 
            mit dem zu schreibenden Content verglichen und 
            nur bei einer Änderung neu geschrieben.
        Rückgabe boolsch: True, wenn echter Schreibvorgang.
    """

    try:
        with open(file_path, 'r') as f:
            oldcontent = f.read()
    except Exception:
        oldcontent = ""
    
    # hier kein try, da ein Fehler unerwarted ist und durchgereicht werden soll.
    if oldcontent != content:
        with open(file_path, 'w') as f:
            f.write(content)
        debug(c_o, f"{file_path} geändert und wurde neu geschrieben")
        return True
    debug(c_o, f"{file_path} ist unverändert - wurde nicht überschrieben")
    return False    
        

def get_title_prio_from_html(htmlfile, ersatztitel=''):
    """ Zuerst wird versucht eine gleichnamige md-Datei zu finden
            und den Titel und die Prio aus YAML zu extrahieren.
        Sonst ist Prio 100 und Titel wird weiter gesucht:
        Dann wird der Titel wird aus dem Header der HTML-Datei geholt.
        Wurde ein Ersatztitel übergeben, so wird dieser mit Prio 100 übernommen.
        Wenn nicht vorhanden oder auf "-" gesetzt, so wird
            der Dateiname ohne Extension als Ersatz gewählt.
    """
    counter = 0
    title = ""
    prio = 1
    
    yamldict = get_yaml_dict_from_md(htmlfile.absolute().parent / (htmlfile.stem + ".md"))
    if yamldict:
        title = yamldict.get("title")
        prio = analyze_priostrg(yamldict.get("m²_sbpriority"))
        # print(f'yamldict for {htmlfile.name} liefert {prio}')
        
    if title:
        return title, prio
        
    prio = 1

    try:
        with htmlfile.open() as hfile:
            for line in hfile:
                counter += 1
                loline = line.lower()
                s = loline.find("<title>")
                if s >= 0:
                    e = loline.find("</title>")
                    if e > s + 7:
                        title = line[s + 7:e]
                        # print(title)
                        if title != "-":
                            return title, prio
    except (FileNotFoundError, UnicodeDecodeError):
        pass
        
    if ersatztitel:             # Hiermit wird z.B. ein Unterverzeichnisname gegenüber "index" priorisiert
        return ersatztitel, prio
    return htmlfile.stem, prio
    
    
def analyze_priostrg(priostrg):
    priostrg = str(priostrg).lower()
    if priostrg.isdigit():
        prioint = int(priostrg)
        prio = 2 if prioint > 100 else (0 if prioint < 100 else 1)   # Kompatibilität zu 100 für normal
    else:
        prio = 2 if priostrg.startswith("h") else (0 if priostrg.startswith("l") else 1) 
    return prio
                    
    
def get_parent_section(path):
    parent_filename, parent_title, parent_dict = get_folder_filename_title_yaml(path.parent)
    
    if parent_filename:    
        parent_output = SIDEBAR_sectionstart.format("&#x21E7; Übergeordnet", "") + \
            SIDEBAR_li_bb[1].format("", '../' + parent_filename, "", "", parent_title, "") + \
            SIDEBAR_sectionendemini
        return parent_output, 1

    return "", 0  # leere Rückgabe, wenn es halt keine auffindbare Datei gibt.
        
        
def get_links_section(path):
    
    d_i_y = path / 'mdm_dir.yaml'
    l_r_output = ''
    l_anzahl = 0
    if d_i_y.is_file():
        ydict = get_yaml_dict_from_yaml(d_i_y)
        if ydict:
            links = ydict.get("m²_links")
            linkoutput, l_anzahl = format_yaml_links(links)
            if linkoutput:
                l_r_output = SIDEBAR_sectionstart.format("&#x2B00; Links", "") + linkoutput + SIDEBAR_sectionendemini
    return l_r_output, l_anzahl
    
    
def format_yaml_links(links):
    linkoutput = ''
    l_anzahl = 0
    if links:
        for linkdict in links:
            link = linkdict.get("link")
            title = linkdict.get("title")
            hover = linkdict.get("hover", "")
            if link and title: 
                l_anzahl += 1
                linkoutput += SIDEBAR_extern.format(link, hover, title)
    return linkoutput, l_anzahl
    
    
def get_files_section(path, relpath="", timeline_list=None, all_files=True):
    """ findet und formatiert Links zu html/PDF-Dateien in demselben Verzeichnis
    """
    isroot = False
    lang = ""
    index_filename, folder_title, ydict = get_folder_filename_title_yaml(path)
    if ydict:
        isroot = bool(ydict.get("m²_isroot"))
        lang = ydict.get("lang")
    li_list = [[], [], []]
    files_output = ''
    if relpath and not relpath.endswith("/"):
        relpath += "/"
    
    vari_br = ''   # hmmm, Altlast?
        
    for htmlfile in path.iterdir():
        if htmlfile.is_file() and \
           htmlfile.suffix.lower() in (".html", ".htm") and \
           htmlfile.stem != "sidebar" and \
           htmlfile.stem != "sitemap" and \
           not htmlfile.stem.startswith("_mdm") and \
           not htmlfile.stem.endswith("_SLIDES") and \
           not htmlfile.stem.endswith("_slides") and \
           '_SLIDES_' not in htmlfile.stem and \
           (all_files or htmlfile.name == index_filename):
               
            # yey, wir haben eine html-Datei gefunden. Sammle dies als Link, mit Title, Priorität und ggf. PDF-File
            title, prio = get_title_prio_from_html(htmlfile)  # prio aus {0 , 1, 2} für Low, Normal, High
            liclass = "nonindex"
            title_prefix = ""
            if htmlfile.name == index_filename:
                prio = 2
                liclass = ""
                title_prefix = "🗁" if all_files else "🗀"
            pdffilename = f'{htmlfile.stem}_A4.pdf'
            if (path / pdffilename).exists() and all_files:
                pdffileentry = SIDEBAR_pdf.format(relpath + pdffilename)
            else:
                pdffileentry = ""
            
            slidesfileentry = ""
            for s_format in SLIDE_FORMATE.keys():
                slidesfilename = f'{htmlfile.stem}_SLIDES_{s_format}.pdf'
                if (path / slidesfilename).exists() and all_files:
                    slidesfileentry += SIDEBAR_slides.format(relpath + slidesfilename, SLIDE_FORMAT_DESC.get(s_format))
            
            li_list[prio].append((title, 
                                  SIDEBAR_li_bb[prio].format(liclass,
                                                             relpath + htmlfile.name,
                                                             title.replace(" ", "-"), 
                                                             "", 
                                                             title_prefix + title, 
                                                             pdffileentry + slidesfileentry)
                                  )) 
            # ein tupel mit (sortierkriterium,inhalt)
            
            # Cool, nun schauen wir, ob weitere Infos aus der .md-Datei gebraucht werden:
            if timeline_list:
                mdfile = path / (htmlfile.stem + ".md")
                if mdfile.is_file():
                    # print(mdfile.name + " wird ausgelesen");
                    yd = get_yaml_dict_from_md(mdfile)
                    date = ""
                    title = ""
                    abstract = ""
                    if yd:
                        date_dt = yd.get("date")
                        title = yd.get("title")
                        abstract = yd.get("abstract")
                        description = yd.get("description")
                        if date_dt and title:
                            date = date_dt.strftime("%d.%m.%Y")
                            if not abstract:
                                abstract = description
                            if not abstract:
                                abstract = ""
                            # print(mdfile.name + " enthält " + date + " " + title);
                        
                            timeline_list.append((date_dt.strftime("%Y-%m-%d"),
                                                  TIMELINE_li.format(date,
                                                                     relpath + htmlfile.name,
                                                                     title.replace(" ", "-"), 
                                                                     abstract,
                                                                     title,
                                                                     folder_title)))
              
    fanzahl = len(li_list[0]) + len(li_list[1]) + len(li_list[2])
    if fanzahl:
        li_list[1].sort()
        if li_list[2]:
            li_list[2].sort()
            li_list[1] = li_list[2] + [("", vari_br)] + li_list[1]
        if li_list[0]:
            li_list[0].sort()
            li_list[1] = li_list[1] + [("", vari_br)] + li_list[0]

        files_output += SIDEBAR_sectionstart.format('', 'class="files"')

        for li in li_list[1]:
            files_output += li[1]
        files_output += SIDEBAR_sectionende

    return files_output, fanzahl, isroot, lang


@dataclass
class RootInfo:  
    fixlink_section: str = ""
    fixlink_count: int = 0
    root_section: str = ""
    lang: str = ""
    updir_string: str = ""
    root_path: str = ""


def get_root_info(c_o, akt_path):
    """ bekommt ein Config_Obj sowie den akt. Path und
        gibt ein RootInfo-Objekt zurück
    """
    updir_count = 0
    updir_string = ""
    filename = ""
    fl_output = ""
    fl_anzahl = 0
    pathlist = []
    pathlistoutput = ""
    
    debug(c_o, "ROOT-Info: START für ", akt_path)

    if not c_o.flag_root_exists:
        return RootInfo()

    # Schleife über alle Verzeichnisse von start bis root
    updir_count = 0
    while True:
        updir_string = ("../" * updir_count)[:-1]
        debug(c_o, f"Root-Info: Aktueller updir_string:'{updir_string}'")
        debug(c_o, f"ROOT-Info: Checke Verzeichnis:{(akt_path / updir_string).resolve()}")
        filename, foldertitle, yd = get_folder_filename_title_yaml((akt_path / updir_string).resolve())
        debug(c_o, "ROOT-Info: Check-Ergebnis fn,ft: ", filename, ", ", foldertitle)
        
        if filename:  # wenigstens wurde irgendeine Indexdatei gefunden
            pathlist.insert(0, (updir_string + "/" + filename, foldertitle))
        else:         # vielleicht können Browser /Webserver das Problem lösen  
            pathlist.insert(0, (updir_string + "/", foldertitle))  
        
        # Ausstieg
        if (akt_path / updir_string / 'mdm_root.yaml').is_file():
            break

        updir_count += 1

    # Nun sind wir bei root angekommen, der erste Eintrag in pathlist ist der des root-Verzeichnisses
    debug(c_o, "ROOT-Info: root erreicht: ", (akt_path / updir_string / filename).resolve())
    
    flinks = c_o.fixlinks
    
    flinkoutput, fl_anzahl = format_yaml_links(flinks)
    
    if flinkoutput:
        fl_output = SIDEBAR_sectionstart.format("&#x2B00; globale Links", "") + flinkoutput + SIDEBAR_sectionende

    rootfirst = True
    nbs = ""
    for fnam, ftit in pathlist:
        if rootfirst:
            # pathlistoutput = SIDEBAR_li_bb[2].format("", updir_string + "/" + filename, "", "", foldertitle, "")
            pathlistoutput = SIDEBAR_li_bb[2].format("", fnam, "", "", ftit, "")
            rootfirst = False
        else:
            pathlistoutput += SIDEBAR_li_bb[1].format("", fnam, "", "", nbs + "&#8618; " + ftit, "")
            nbs += "&numsp;&numsp;"
            
    # debug(c_o, "ROOT-Info: PathListOutput:\n" + pathlistoutput)
    
    root_section = \
        SIDEBAR_sectionstart.format('&#8962;', "") + \
        pathlistoutput + \
        SIDEBAR_sectionende
    
    return RootInfo(fl_output, fl_anzahl, root_section, c_o.lang, updir_string, (akt_path / updir_string).resolve())
    
   
def get_folder_filename_title_yaml(folder_path):
    """ Liefert nach bestem Bemühen 
        1 den Dateinamen der indexdatei eines Verzeichnisses und 
        2 den anzugebenden Title des Verzeichnisses:
            * den per overridetitle festgelegten oder, wenn leer,
            * den Title der indexdatei oder, wenn leer,
            * den Namen des Verzeichnisses
        3 das YAML-Dict, welches ggf. mehr Infos liefert
        * Strings sind leer, wenn keine Datei gefunden wurde
    """
    # Vorbereitung
    d_i_y = folder_path / 'mdm_dir.yaml'
    # print("Lese Folder-Info von ", d_i_y)
    folder_title = ''
    folder_filename = ''
    d_i_y_dict = {}
    if d_i_y.is_file():
        # d_i_y einlesen in d_i_y_dict
        d_i_y_dict = get_yaml_dict_from_yaml(d_i_y)
        if d_i_y_dict:
            folder_filename = d_i_y_dict.get("m²_indexfilename")
            folder_title = d_i_y_dict.get("m²_overridetitle")    # eigentlich unlogisch, aber wenn der User es will...
    if not folder_filename or not (folder_path / folder_filename).is_file():
        folder_filename = 'index.html'
    if not (folder_path / folder_filename).is_file():
        folder_filename = 'index.htm'
    
    if (folder_path / folder_filename).is_file():      # muss ja irgenwann mal
        if not folder_title:  # jetzt holen wir's lieber aus der Datei; notfalls Verzeichnisname
            folder_title, _ = get_title_prio_from_html(folder_path / folder_filename, folder_path.name)
        return folder_filename, folder_title, d_i_y_dict 
        
    return "", folder_path.name, {}  # fast leere Rückgabe, wenn es halt keine auffindbare Datei gibt.

