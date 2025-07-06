try:
    import yaml  # Quelle unter debian: python3-yaml, sonst pyyaml per pip
except Exception:
    print('''Fehler!\nPyYaml muss installiert sein!
        Installiere entweder python3-yaml unter Debian 
        oder pip pyyaml.''')
    exit()

""" Erzeugt entweder aus dem
        optionalen YAML-Kopf einer Markdown-Datei oder aus einem reinen
        YAML-File das entsprechende und gibt es zurück.
        
        Der md-Kopf muss dazu mit --- und/oder ___ starten und enden.
"""

def get_yaml_dict_from_md(mdfile):
    """ Liest aus der md-Datei den YAML-Bereich und konvertiert ihn zu einem dict.
        Feste Vorgabe: Beginnt als erste Zeile mit drei ---, endet mit drei ... am Zeilenanfang.
        Bei Fehler: Leeres dict.
    """
    yaml_block = ''
    yaml_dict = {}
    try:
        with mdfile.open() as f:
            line = f.readline()
            if line.startswith("---") or line.startswith("..."):
                line = f.readline()
                while line:
                    if not (line.startswith("---") or line.startswith("...")):
                        yaml_block += line
                    else:
                        yaml_dict = yaml.safe_load(yaml_block)
                        break
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
    
