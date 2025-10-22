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
    reading_yaml = False

    # Nun eine schlichte State Machine:
    try:
        with mdfile.open() as f:
            for line in f:
                if (line.startswith("---") or line.startswith("...")):
                    if not reading_yaml:
                        reading_yaml = True
                    else:
                        return valides_yaml_dict(yaml.safe_load(yaml_block))
                        
                elif reading_yaml: 
                    yaml_block += line
    except Exception:
        pass                # nicht lesbar = nicht interessant...

    return yaml.safe_load("m²_yaml_load_error: True") 
    
    
def get_yaml_dict_from_yaml(yamlfile):
    """ Liest reines YAML ein und konvertiert zu einem dict.
        Bei Fehler: Leeres dict.
    """
    yaml_dict = {} 
    try:
        with yamlfile.open() as f:
            yaml_dict = yaml.safe_load(f)
    except Exception:
        pass               # nicht lesbar = nicht interessant...
    return valides_yaml_dict(yaml_dict)


def get_yaml_value_2_list(entry, default=[]):
    # was immer als entry aus einem yaml-dict geliefert wurde, wird nun als Liste zurückgegeben
        
    if isinstance(entry, list):
        return [str(x).lower() for x in entry]
    elif entry:
        return [str(entry).lower()]
    elif isinstance(default, list):
        return default      # Dummywert
    else:
        return [default]

def valides_yaml_dict(yaml_dict):
    try:
        irgendeinwert = yaml_dict.get("irgeneinschluessel")
        return yaml_dict
    except AttributeError:
        return yaml.safe_load("m²_yaml_load_error: True") 