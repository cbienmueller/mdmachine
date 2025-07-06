""" Erzeugt aus 
        dem Filelisting und 
        meinen Namenskonventionen
        
        eine Siedbar, mit Links zu den Dateien und Verzeichnissen.
        Fehlt: Mehr Doku zu dir_info.yaml und Inhalten der Unterverzeichnisse.
"""
from dataclasses import dataclass

from mdmwrx.yamlread import get_yaml_dict_from_yaml, get_yaml_dict_from_md
from mdmwrx.converter import SLIDE_FORMATE, SLIDE_FORMAT_DESC


SB_VERBOSE = False

DEMO_DIR_INFO_YAML = """
## dir_info.yaml
## Enthält 2 Informationsblöcke für die Sidebars und die sitemap

## 1. Info zu diesem Verzeichnis
##      Wird für sidebar des Elternverzeichnisses oder als root in Kindverzeichnissen ausgewertet
##
##      indexfilename: xyz.html
##          als Alternative zur index.html
##
#m²-indexfilename: demo.html
##
##      overridetitle: Demoinhalte
##          Eigentlich sollte der Verzeichnistitel der Datei indexfilename entnommen werden.
##          Dies kann hier übersteuert werden (kann inkonsistent wirken)
#m²-overridetitle: Demoinhalte
##
##      isroot: False 
##          Flag, ob DIESES Verzeichnis ab hier als Home / Root 
##          des darunterliegenden Verzeichnisbaums anzusehen ist. 
##          Der Linktitel wird der Datei oder ggf. obigem overridetitle entnommen.
#m²-isroot: True
##
##      subdirprio: High oder Low
##          Wird damit in der sidebar des übergeordneten Verzeichnisses einsortiert.
##          Dort werden High/normal/Low in drei Blöcken, jeweils in sich alphabetisch sortiert
##          angeordnet im Format Fett/normal/kursiv.
#m²-subdirprio: Low
##      
##      lang: Sprachstring
##          welche Sprache soll als HTML lang Wert gesetzt werden.
##          Wert im Markdown-YAML-Block überschreibt dies.
#lang: "de-DE"
     

## 2. Linklisten
##      links ist ein array of dicts (welche link, title und hover als keys enthalten).
##          * Die Links werden am Ende der Sidebar als einzelne Links aufgeführt.
##          * title ist der Anzeigename
##          * hover wird angezeigt, wenn die Maus über den Link gleitet.
##          Sichtbarkeit: Sie sind also neben jeder Seite dieses Verzeichnisses sichtbar
##          Anzahl: Kein Limit...
##
#m²-links:
#    - link:  'http://example.com'
#      title: 'Example-homepage'
#    - link:  'https://www.google.com'
#      title: 'Let's Search something'
#      hover: 'go to google'
##
##      m²-fixlinks: wie oben "links", werden aber nur beachtet, wenn isroot = True ist
##          Sichtbarkeit: Sie sind also neben jeder Seite dieses und aller untergeordneten Verzeichnisse sichtbar
##          Ausnahme: Wenn einuntergeordnetes selbst wieder isroot gesetzt hat.
#m²-fixlinks:
#    - link:  'http://example.de'
#      title: 'Deutsche Homepage'
"""

FILE_barebone = """<!DOCTYPE html>
<html lang="{}">
<head>
    <meta charset="utf-8" />
    <meta name="generator" content="mdmachine" />
    <title>{}</title>
    <link rel="Stylesheet" type="text/css" href="https://www.bienmueller.de/css/cb.css">
    <link rel="Stylesheet" type="text/css" href="https://www.bienmueller.de/css/cb_sb.css">
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

TIMELINE_li = '\t\t<li>{} <a href="{}" id="{}" title="{}" target="_parent">{}</a></li>\n'

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


def write_demo_dir_info_yaml(path):
    i = -1
    while i < 10:
        i += 1
        le_path = path / ("dir_info.yaml.blank" + (str(i) if i else ""))
        # print(le_path)
        if not le_path.is_file():
            i = 99
    with open(le_path, 'w') as f:
        f.write(DEMO_DIR_INFO_YAML)
    return str(le_path)
        

def make_sitemap(path):
    sm_path = path / 'sitemap.html'
    tl_path = path / '_mdm_timeline.html'
    timeline_list = [("2024-01-01", "dummy")]
    lang = "de"
    with open(sm_path, 'w') as f:
        # ## Dateistart
        content, lang = get_folderinfo4sitemap(path, "", timeline_list)  
        # wird rekursiv für jedes Unterverzeichnis aufgerufen
        # lang kommt nur vom root-dir_info.yaml
        # timeline_list nimmt Datum und Beschreibungstext auf
        f.write(SIDEBAR_barebone.format(lang, 'Sitemap'))
        f.write(content)
        f.write(SIDEBAR_fine)
        
    with open(tl_path, 'w') as f:
        del timeline_list[0]  # dort ist nur ein Dummy
        timeline_list.sort(key=lambda tup: tup[0], reverse=True)        # sorts in place
        f.write(TIMELINE_barebone.format(lang, 'TimeLine'))
        for d, h in timeline_list[:16]:
            f.write(h)
        f.write(TIMELINE_fine)


def make_new_sidenavi(aktpath):
    with open(sm_path, 'w') as f:
        content, lang = get_side_navi(aktpath)
        f.write(SIDEBAR_barebone.format(lang, 'Sitemap'))
        f.write(content)
        f.write(SIDEBAR_fine)


def get_side_navi(aktpath):
    ri = get_root_info(aktpath)
    startpath = ri.root_path
    timeline_list_dummy = [("2024-01-01", "dummy")]
    lang = "de"
    content, lang = get_folderinfo4sitemap(startpath, ri.updir_string, timeline_list_dummy, aktpath)
    # wird rekursiv für jedes Unterverzeichnis aufgerufen
    # lang kommt nur vom root-dir_info.yaml
    # timeline_list nimmt Datum und Beschreibungstext auf
    # Enthält nur im aktpath die Dateien
    return content, lang
        
        
def get_folderinfo4sitemap(mypath, relpath, timeline_list, filespath=""):
    ''' mypath ist das wirklich zu analysierende Verzeichnis.
        relpath ist der zu den Links zu addierende path, der den Ort relativ zum Verzeichnis von make_sitemap angibt.
        timeline_list nimmt Datei-Datum-Pärchen auf.
        filespath ist (wenn gesetzt) der einzige Pfad, bei dem Files mit aufgeführt werden. Sonst nur Verzeichnisse.
    '''
    if SB_VERBOSE:
        print("gfi4sm ", mypath, "!")
    if not mypath:
        return "", ""
    filename, foldertitle, yd = get_folder_filename_title_yaml(mypath)
    if yd:
        lang = yd.get("lang")
    else:
        lang = ""
    if filename and foldertitle:
        if relpath and not relpath.endswith("/"):
            relpath += "/"
        smf_output = ""
        
        if filespath: 
            print(filespath, mypath)
        if not filespath or mypath == filespath:
            all_files = True
        else:
            all_files = False
        l_section, _, _, _ = get_files_section(mypath, relpath, foldertitle, timeline_list, all_files)
        smf_output += l_section

        smf_sub_output = ""
        for subdir in mypath.iterdir():
            if subdir.is_dir():
                print("recurse sitemap -> " + subdir.name)
                content, _ = get_folderinfo4sitemap(subdir, relpath + subdir.name, timeline_list, filespath)
                smf_sub_output += content
        if smf_sub_output:
            smf_output += SIDEBAR_sectionstart.format("", "")
            smf_output += smf_sub_output
            smf_output += SIDEBAR_sectionende
        return smf_output, lang
    return "", ""


def make_sidebar(path, do_recursive=False, talk=""):
    ausgabe = path / 'sidebar.html'
    
    ri = get_root_info(path)
    navi_content, lang = get_side_navi(path)
    
    with open(ausgabe, 'w') as f:
        
        f.write(SIDEBAR_barebone.format(lang, 'Navigation'))
        f.write(navi_content)               # komplette Navigation
        f.write('\t<hr>\n')                 # Trennlinie
        
        link_section, isroot_flag, l_anzahl = get_links_section_isroot(path)
        
        f.write(link_section) 

        if (link_section and ri.fixlink_section):
            f.write('\t<hr>\n')                 # Trennlinie

        f.write(ri.fixlink_section)

        f.write(SIDEBAR_fine)
    
    if do_recursive:
        for subdir in path.iterdir():
            if subdir.is_dir():
                print("recurse sidebar -> " + subdir.name)
                make_sidebar(subdir, do_recursive, talk)


def make_sidebar_ORG(path, do_recursive=False, talk=""):
    ausgabe = path / 'sidebar.html'
    p_anzahl = 0
    
    with open(ausgabe, 'w') as f:
        
        # ## Was bietet root?
        # fixlinks, rootelement, lang, fl_anzahl 
        ri = get_root_info(path)
            
        # ## Liste der Dateien im Verzeichnis ermitteln
        filessection, f_anzahl, isroot, lang2 = get_files_section(path)
        
        if lang2:
            lang = lang2
        else:
            lang = ri.lang
        
        # ## Dateistart ausgeben
        f.write(SIDEBAR_barebone.format(lang, 'Navigation'))
        
        if ri.root_section:
            f.write(ri.root_section)            # enthält Pfad bis zum aktuellen Verzeichnis
        
        if ri.root_section and filessection:    # nur wenn es beides gibt, kommt Trennzeile
            f.write('\t<hr>\n')
        
        if filessection:                    # enthält Dateien im Verzeichnis
            f.write(filessection)
                    
        f.write('\t<hr>\n')                 # Trennlinie
        
        if not isroot:
            par_section, p_anzahl = get_parent_section(path)
            if p_anzahl:
                f.write(par_section) 
                
        subs_section, s_anzahl, subnamen = get_subdirs_section(path)
        if subnamen:
            subnamen = f'({subnamen})'
        if subs_section:
            f.write(subs_section)
        
        link_section, isroot_flag, l_anzahl = get_links_section_isroot(path)
        
        f.write(link_section) 
                
        f.write(ri.fixlink_section)

        f.write(SIDEBAR_fine)
    if talk != "silent":
        print("┌─Sidebar-Zusammenfassung:")
        if talk:
            print("│ " + talk)
        print(f'│ sidebar.html erstellt mit\n│ {f_anzahl: >5} eingetragenen Seiten '
              f' sowie\n│ {s_anzahl: >5} Unterverzeichnissen {subnamen}'
              f' bzw. \n│ {p_anzahl: >5} Oberverzeichnis'
              f' und  \n│ {l_anzahl: >5} Links'
              f' und  \n│ {fl_anzahl: >5} Fixlinks')
              
    if do_recursive:
        for subdir in path.iterdir():
            if subdir.is_dir():
                print("recurse sidebar -> " + subdir.name)
                make_sidebar(subdir, do_recursive, talk)


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
        prio = analyze_priostrg(yamldict.get("m²-sbpriority"))
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
                    
    
def get_subdirs_section(path):
    li_list = [[], [], []]
    subs_output = ''
    subname_list = []
    
    for subdir in path.iterdir():
        if subdir.is_dir():
            subname_list.append(subdir.name)
            indexfilename = ""
            subdirprio = 1
            subdirtitel = ""
            if (subdir / "dir_info.yaml").exists():  # Gibt es dir_info.yaml im Unterverzeichnis?
                #  print("s "+subdir.name+" hat yaml")
                subdict = get_yaml_dict_from_yaml(subdir / "dir_info.yaml")
                if subdict:
                    indexfilename = subdict.get("m²-indexfilename")
                    if indexfilename:
                        indexfilename = indexfilename.replace("/", "_")
                        indexfilename = f'{subdir.name}/{indexfilename}'
                    subdirtitel = subdict.get("overridetitel")  # doof, besser wäre der Titel des indexfiles, s.u.
                    subdirprio = analyze_priostrg(subdict.get("subdirprio"))
                
            if (not indexfilename) or (not (path / indexfilename).exists()):
                indexfilename = f'{subdir.name}/index.html'
            if not (path / indexfilename).exists():
                indexfilename = f'{subdir.name}/index.htm'
                                
            if (path / indexfilename).exists():
                if not subdirtitel:
                    subdirtitel, prio = get_title_prio_from_html((path / indexfilename), subdir.name)
                
                li_list[subdirprio].append((subdirtitel, 
                                           SIDEBAR_li_bb[subdirprio].format("", indexfilename, "", "", subdirtitel, "")))  
                # ein tupel mit (sortierkriterium,inhalt)
    s_anzahl = len(li_list[0]) + len(li_list[1]) + len(li_list[2])
    if s_anzahl:
        li_list[1].sort()
        if li_list[2]:
            li_list[2].sort()
            li_list[1] = li_list[2] + [("", '<br>\n')] + li_list[1]
        if li_list[0]:
            li_list[0].sort()
            li_list[1] = li_list[1] + [("", '<br>\n')] + li_list[0]

        subs_output += SIDEBAR_sectionstart.format("&#x21E9; Unterkategorien", "")

        for li in li_list[1]:
            subs_output += li[1]
        subs_output += SIDEBAR_sectionendemini

    return subs_output, s_anzahl, ", ".join(subname_list)


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
    sby = folder_path / 'dir_info.yaml'
    # print("Lese Folder-Info von ", sby)
    folder_title = ''
    folder_filename = ''
    sby_dict = {}
    if sby.is_file():
        # sby einlesen in sby_dict
        sby_dict = get_yaml_dict_from_yaml(sby)
        if sby_dict:
            folder_filename = sby_dict.get("m²-indexfilename")
            folder_title = sby_dict.get("m²-overridetitle")    # eigentlich unlogisch, aber wenn der User es will...
    if not folder_filename or not (folder_path / folder_filename).is_file():
        folder_filename = 'index.html'
    if not (folder_path / folder_filename).is_file():
        folder_filename = 'index.htm'
    
    if (folder_path / folder_filename).is_file():      # muss ja irgenwann mal
        if not folder_title:  # jetzt holen wir's lieber aus der Datei; notfalls Verzeichnisname
            folder_title, _ = get_title_prio_from_html(folder_path / folder_filename, str(folder_path.name))
        return folder_filename, folder_title, sby_dict 
        
    return "", folder_path.name, {}  # fast leere Rückgabe, wenn es halt keine auffindbare Datei gibt.
    
    
def get_parent_section(path):
    parent_filename, parent_title, parent_dict = get_folder_filename_title_yaml(path.parent)
    
    if parent_filename:    
        parent_output = SIDEBAR_sectionstart.format("&#x21E7; Übergeordnet", "") + \
            SIDEBAR_li_bb[1].format("", '../' + parent_filename, "", "", parent_title, "") + \
            SIDEBAR_sectionendemini
        return parent_output, 1

    return "", 0  # leere Rückgabe, wenn es halt keine auffindbare Datei gibt.
        
        
def get_links_section_isroot(path):
    
    sby = path / 'dir_info.yaml'
    isroot = False
    l_r_output = ''
    l_anzahl = 0
    if sby.is_file():
        ydict = get_yaml_dict_from_yaml(sby)
        if ydict:
            isroot = bool(ydict.get("m²-isroot"))
            links = ydict.get("m²-links")
            linkoutput, l_anzahl = format_yaml_links(links)
            if linkoutput:
                l_r_output = SIDEBAR_sectionstart.format("&#x2B00; Links", "") + linkoutput + SIDEBAR_sectionendemini
    return l_r_output, isroot, l_anzahl
    
    
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
    
    
def get_files_section(path, relpath="", sectiontitle="", timeline_list=None, all_files=True):
    """ findet und formatiert Links zu html/PDF-Dateien in demselben Verzeichnis
    """
    isroot = False
    lang = ""
    index_filename, _, ydict = get_folder_filename_title_yaml(path)
    if ydict:
        isroot = bool(ydict.get("m²-isroot"))
        lang = ydict.get("lang")
    li_list = [[], [], []]
    files_output = ''
    if relpath and not relpath.endswith("/"):
        relpath += "/"
    if False:  # all_files:
        if sectiontitle:
            vari_br = ''
            sectiontitle = '&#x21D8; ' + sectiontitle
        else:
            vari_br = '<br>'
            sectiontitle = '&#x21E8; Seiten'
    else:
        vari_br = ''
        sectiontitle = ''
        
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
            if htmlfile.name == index_filename:
                prio = 2
                liclass = ""
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
                                                             title, 
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
                                                                     title)))
              
    fanzahl = len(li_list[0]) + len(li_list[1]) + len(li_list[2])
    if fanzahl:
        li_list[1].sort()
        if li_list[2]:
            li_list[2].sort()
            li_list[1] = li_list[2] + [("", vari_br)] + li_list[1]
        if li_list[0]:
            li_list[0].sort()
            li_list[1] = li_list[1] + [("", vari_br)] + li_list[0]

        files_output += SIDEBAR_sectionstart.format(sectiontitle, 'class="files"')

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


def get_root_info(path):
    """ gibt ab jetzt ein RootInfo-Objekt zurück
    """
    
    """ ...gibt drei Strings und eine Zahl zurück:
        * str: die unter fixlinks abgelegten Links komplett als Section
        * str: die Root-Section, mit allen Verzeichnissen von dort bis zum aktuellen.
        * str: den lang-Parameter
        * die Anzahl der fixlinks
    """
    debug = False
    updir_count = 0
    updir_string = ""
    filename = ""
    fl_output = ""
    fl_anzahl = 0
    pathlist = []
    pathlistoutput = ""
    isrootflag = False
    lang = ""
    
    while not isrootflag and len(str((path / updir_string).resolve())) > 1:
        if debug: 
            print("ROOT-Suche: Checke ", (path / updir_string).resolve())
        filename, foldertitle, yd = get_folder_filename_title_yaml((path / updir_string).resolve())
        if yd:
            isrootflag = yd.get("m²-isroot")
            lang2 = yd.get("lang")
            if not lang:
                lang = lang2    # so wird lang auf den Wert in der nähesten Vorgänger-dir-info.yaml gesetzt
        if debug: 
            print("ROOT-Suche: Check-Ergebnis fn,ft,ir;", filename, ", ", foldertitle, ", ", isrootflag)
        if isrootflag:  # abschließen
            if debug: 
                print("ROOT-Suche: gefunden als ", (path / updir_string / filename).resolve())
            flinks = yd.get("m²-fixlinks")
            
            flinkoutput, fl_anzahl = format_yaml_links(flinks)
            
            if flinkoutput:
                fl_output = SIDEBAR_sectionstart.format("&#x2B00; globale Links", "") + flinkoutput + SIDEBAR_sectionende

            if pathlist:
                nbs = ""
                for fnam, ftit in pathlist:
                    pathlistoutput += SIDEBAR_li_bb[1].format("", fnam, "", "", nbs + "&#8618; " + ftit, "")
                    nbs += "&numsp;&numsp;"
                    
            if updir_string:
                if debug: 
                    print("ROOT-Suche: PathListOutput:\n" + pathlistoutput)
                root_section = \
                    SIDEBAR_sectionstart.format('&#8962;', "") + \
                    SIDEBAR_li_bb[2].format("", updir_string + "/" + filename, "", "", foldertitle, "") + \
                    pathlistoutput + \
                    SIDEBAR_sectionende
                return RootInfo(fl_output, fl_anzahl, root_section, lang, updir_string, (path / updir_string).resolve())
                # fl_output,                     root_section,                     lang,                     fl_anzahl
            else:
                return RootInfo(fl_output, fl_anzahl, 
                                SIDEBAR_sectionstart.format('&#8962;', "") + 
                                SIDEBAR_li_bb[2].format("", filename, "", "", foldertitle, "") + 
                                SIDEBAR_sectionende, 
                                lang, 
                                updir_string, (path / updir_string).resolve())
                return fl_output, \
                    SIDEBAR_sectionstart.format('&#8962;', "") + \
                    SIDEBAR_li_bb[2].format("", filename, "", "", foldertitle, "") + \
                    SIDEBAR_sectionende, \
                    lang, \
                    fl_anzahl
        elif filename:  # wenigstens wurde irgendeine Indexdatei gefunden
            if updir_string:
                pathlist.insert(0, (updir_string + "/" + filename, foldertitle))
            else:
                pathlist.insert(0, (filename, foldertitle))
                
            updir_count += 1
            updir_string = ("../" * updir_count)[:-1]
            print(updir_string)
        else:           # Keine Indexdatei: Abbruch!
            return RootInfo()
    
    return RootInfo()

