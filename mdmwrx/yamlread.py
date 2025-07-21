""" Erzeugt entweder aus dem
        optionalen YAML-Kopf einer Markdown-Datei oder aus einem reinen
        YAML-File das entsprechende und gibt es zurück.
        
        Der md-Kopf muss dazu mit --- und/oder ... starten und enden.
        Pandoc ist dabei aber kritischer: Start:--- Ende:...
"""

try:
    import yaml  # Quelle unter debian: python3-yaml, sonst pyyaml per pip
except Exception:
    print('''Fehler!\nPyYaml muss installiert sein!
        Installiere entweder python3-yaml unter Debian 
        oder pip pyyaml.''')
    exit()


def get_yaml_dict_from_md(mdfile):
    """ Liest aus der md-Datei den YAML-Bereich und konvertiert ihn zu einem dict.
        Feste Vorgabe: Beginnt als erste Zeile mit drei ---, endet mit drei ... am Zeilenanfang.
        Bei Fehler: Leeres dict.
    """
    yaml_block = ''
    yaml_dict = {}
    reading = True
    try:
        with mdfile.open() as f:
            line = f.readline().strip()
            # Überspringe führende (illegale) Leerzeilen:
            while not line.strip():
                line = f.readline()
            
            if line.startswith("---") or line.startswith("..."):
                line = f.readline()
                while reading:
                    if line.strip() and \
                       (line.startswith("---") or line.startswith("...")):
                        reading = False
                        yaml_dict = yaml.safe_load(yaml_block)
                        break
                    yaml_block += line
                    line = f.readline()
    except Exception:
        pass                # nicht lesbar = nicht interessant...
    return yaml_dict
    
    
def get_yaml_dict_from_yaml(yamlfile):
    """ Liest reines YAML ein und konvertiert zu einem dict.
        Bei Fehler: Leeres dict.
    """
    yaml_dict = {}
    try:
        with yamlfile.open() as f:
            yaml_dict = yaml.safe_load(f)
    except Exception:
        pass                # nicht lesbar = nicht interessant...
    return yaml_dict
    
