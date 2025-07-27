""" config.py

    liest nach Möglichkeit eine mdm_root.yaml ein und setzt allgemeine Werte wie CSS-Datei-URLs.
    Bei Fehlen wird der Verzeichnisbaum nach oben gegangen.
    Bei endgültigem Fehlen werden Standardwerte angenommen um ein Funktionieren sicherzustellen.
"""

# Batteries
from dataclasses import dataclass
from pathlib import Path


# MDMWRX
from mdmwrx.yamlread import get_yaml_dict_from_yaml
# from mdmwrx.sidebar get_folder_filename_title_yaml

debug = True


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
    fixlinks: list[tuple]       # (URL, title)
    flag_gen_sitemap: bool
    lang: str
    

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
                yd.get("m²_cssfile_main"),
                yd.get("m²_cssfile_md"),
                yd.get("m²_cssfile_sb"),
                yd.get("m²_mainfont"),
                yd.get("m²_fixlinks"),
                yd.get("m²_generate_sitemap", False),
                yd.get("m²_lang", "de-DE")
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
                    'https://www.bienmueller.de/css/cb.css',
                    'https://www.bienmueller.de/css/cb_md.css',
                    'https://www.bienmueller.de/css/cb_sb.css',
                    'https://www.bienmueller.de/fonts/RadioCanadaRegular.woff2',
                    [],
                    False,
                    "de-DE"

                )
