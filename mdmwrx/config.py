""" config.py

    liest nach Möglichkeit eine mdm_root.yaml ein und setzt allgemeine Werte wie CSS-Datei-URLs.
    Bei Fehlen wird der Verzeichnisbaum nach oben gegangen.
    Bei endgültigem Fehlen werden Standardwerte angenommen um ein Funktionieren sicherzustellen.
"""

# Batteries
from dataclasses import dataclass
from pathlib import Path


# MDMWRX
from mdmwrx.yamlread import get_yaml_dict_from_yaml, get_yaml_value_2_list
# from mdmwrx.sidebar get_folder_filename_title_yaml
# from mdmwrx.tools import debug


@dataclass
class Config_Obj:  
    startpath: Path
    rootpath: Path              # nur gültig, wenn root_exists
    medien_path: Path
    dir_count: int              # Verzeichnisanzahl zw. root und start (1 bei is_root, 0 wenn root_exists==False)
    flag_dir_is_root: bool      # Quasi die Info, ob obige Pfade identisch sind
    flag_root_exists: bool      # ob die Datei mdm_root.yaml überhaupt existiert
    cssfile_main: str           # URL
    cssfile_md: str             # URL
    cssfile_sb: str             # URL
    mainfont: str               # URL
    fixlinks: list[tuple]       # (URL, title, hover)
    inc_style_list: list[str]   # List of Strings als Namensbestandteile
    lang: str                   # HTML-lang-Parameter
    flag_gen_sitemap: bool      # Soll automatisch eine sitemap (im root-Verzeichnis) geführt werden?
    flag_gen_sidebar: bool      # Soll auch ohne dir_yaml automatisch eine sidebar (Navigation) in jedem Verzeichnis 
    #                           #   mit html-Dateien geführt werden?
    flag_verbose: bool          # für Ausgabe von Debug-Informationen
    

def get_config_obj(startpath, medien_path):   # Pfad ist schon resolved
    rootpath = startpath
    flag_dir_is_root = True
    flag_root_exists = False
    dir_count = 1
    # Schritt 1: rool suchen
    while True:
        if (rootpath / 'mdm_root.yaml').is_file():
            print("mdm_root.yaml found at ", rootpath)
            flag_root_exists = True
            # Schritt 2a: Gefunden und Auslesen
            yd = get_yaml_dict_from_yaml(rootpath / 'mdm_root.yaml')
            
            return Config_Obj(
                startpath,
                rootpath,
                medien_path,
                dir_count,
                flag_dir_is_root,
                flag_root_exists, 
                yd.get("m²_cssfile_main", 'https://www.bienmueller.de/css/mdm_main.css'),
                yd.get("m²_cssfile_md", 'https://www.bienmueller.de/css/mdm_md.css'),
                yd.get("m²_cssfile_sb", 'https://www.bienmueller.de/css/mdm_sb.css'),
                yd.get("m²_mainfont", 'https://www.bienmueller.de/fonts/OpenSansRegular.woff2'),
                yd.get("m²_fixlinks"),
                get_yaml_value_2_list(yd.get("m²_include_style")),
                yd.get("m²_lang", "de-DE"),
                yd.get("m²_generate_sitemap", False),
                yd.get("m²_generate_sidebar", False),
                yd.get("m²_verbose", False)
            )
            
        else:
            flag_dir_is_root = False  # es gab nur eine Chance
            rootpath = rootpath.parent
            dir_count += 1
            if len(str(rootpath)) <= 2:
                # Schritt 2b: Nicht gefunden, also Standardwerte einsetzen
                return Config_Obj(
                    startpath,
                    rootpath,
                    medien_path,
                    0,
                    False,
                    False,
                    'https://www.bienmueller.de/css/mdm_main.css',
                    'https://www.bienmueller.de/css/mdm_md.css',
                    'https://www.bienmueller.de/css/mdm_sb.css',
                    'https://www.bienmueller.de/fonts/OpenSansRegular.woff2',
                    [],
                    [],
                    "de-DE",
                    False,
                    False,
                    False

                )
