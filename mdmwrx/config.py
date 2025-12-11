""" config.py

    liest nach Möglichkeit eine mdm_root.yaml ein und setzt allgemeine Werte wie CSS-Datei-URLs.
    Bei Fehlen wird der Verzeichnisbaum nach oben gegangen.
    Bei endgültigem Fehlen werden Standardwerte angenommen um ein Funktionieren sicherzustellen.
"""

# Batteries
from dataclasses import dataclass, field
from pathlib import Path
from shutil import which




# MDMWRX
from mdmwrx.yamlread import get_yaml_dict_from_yaml


BROWSER_ENGINES = ['google-chrome', 'chromium', 'brave-browser']

@dataclass
class Config_Obj:  
    startpath: Path
    rootpath: Path              # nur gültig, wenn root_exists
    medien_path: Path
    browser_engine: str
    dir_count: int              # Verzeichnisanzahl zw. root und start (1 bei is_root, 0 wenn root_exists==False)
    flag_dir_is_root: bool      # Quasi die Info, ob obige Pfade identisch sind
    flag_root_exists: bool      # ob die Datei mdm_root.yaml überhaupt existiert
    cssfile_main: str           # URL
    cssfile_md: str             # URL
    cssfile_sb: str             # URL
    mainfont: str               # URL
    fixlinks: list[tuple]       # (URL, title, hover)
    inc_style_list: list[str]   # List of Strings als Namensbestandteile
    inc_css_list: list[str]     # List of Strings als (zu root) relative css-Pfade
    inc_main_css: str           # Eine CSS-Datei, die auch für Sidefiles verwendet wird (-> Farbdefinitionen)
    lang: str                   # HTML-lang-Parameter
    flag_gen_sitemap: bool      # Soll automatisch eine sitemap (im root-Verzeichnis) geführt werden?
    flag_gen_sidebar: bool      # Soll auch ohne dir_yaml automatisch eine sidebar (Navigation) in jedem Verzeichnis 
    #                           #   mit html-Dateien geführt werden?
    flag_verbose: bool          # für Ausgabe von Debug-Informationen
    flag_sup_pdf: bool          # PDF-Erzeugung unterdrücken
    flag_gen_slides: bool       # Slides erzeugen?
    lastconverted: dict = field(default_factory=dict)  # Nimmt Zeitstempel von Konvertierungen auf.

def get_config_obj(startpath, medien_path):   # Pfad ist schon resolved
    # Schritt 1: Browser-Engine checken
    browser_engine = ""
    for engine in BROWSER_ENGINES:
        if which(engine):
            browser_engine = engine
            break 
        
    rootpath = startpath
    # Schritt 2: root suchen
    relpath = relpath_2_root(startpath)
    if not relpath:
        print("Found no mdm_root.yaml.")
        return Config_Obj(
            startpath,
            rootpath,
            medien_path,
            browser_engine,
            0,
            False,
            False,
            'https://www.bienmueller.de/css/mdm_main.css',
            'https://www.bienmueller.de/css/mdm_md.css',
            'https://www.bienmueller.de/css/mdm_sb.css',
            'https://www.bienmueller.de/fonts/OpenSansRegular.woff2',
            [],
            [],
            [],
            "",
            "de-DE",
            False,
            False,
            False,
            False,
            False
        )

    flag_dir_is_root = (relpath == ".")
    flag_root_exists = True
    rootpath = (startpath / relpath).resolve()
    
    print("Found mdm_root.yaml at ", rootpath)
    yd = get_yaml_dict_from_yaml(rootpath / 'mdm_root.yaml')
    return Config_Obj(
        startpath,
        rootpath,
        medien_path,
        browser_engine,
        relpath.count("/"),
        flag_dir_is_root,
        flag_root_exists, 
        yd.get("m²_cssfile_main", 'https://www.bienmueller.de/css/mdm_main.css'),
        yd.get("m²_cssfile_md", 'https://www.bienmueller.de/css/mdm_md.css'),
        yd.get("m²_cssfile_sb", 'https://www.bienmueller.de/css/mdm_sb.css'),
        yd.get("m²_mainfont", 'https://www.bienmueller.de/fonts/OpenSansRegular.woff2'),
        yd.get("m²_fixlinks"),
        yd.get_list_lowered("m²_include_style"),
        yd.get_list("m²_include_css"),
        yd.get("m²_include_main_css", ""),
        yd.get("m²_lang", "de-DE"),
        yd.get("m²_generate_sitemap", False),
        yd.get("m²_generate_sidebar", False),
        yd.get("m²_verbose", False),
        yd.get("m²_suppress_pdf", False),
        yd.get("m²_generate_slides", False)
    )
    
            
def relpath_2_root(path):
    """ Gibt den relativen Pfad (z.B. "./../..") zum Root-Verzeichnis zurück
        Ohne Root-Verzeichnis: Leerer String
        Bereits im Root-Verzeichnis: "."
    """
    relpath = "."
    while len(str((path / relpath).resolve())) > 1:
        if (path / relpath / 'mdm_root.yaml').is_file():
            return relpath
        relpath += '/..'

    # jetzt in Root des Filesystems
    if (path / relpath / 'mdm_root.yaml').is_file():
        return relpath
    return ""    