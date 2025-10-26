""" Erzeugt entweder aus dem
        optionalen YAML-Kopf einer Markdown-Datei oder aus einem reinen
        YAML-File das entsprechende und gibt es zurück.
        
        Der md-Kopf muss dazu mit --- und/oder ... starten und enden.
        Pandoc ist dabei aber kritischer: Start:--- Ende:...
"""

# not Batteries:
try:
    import yaml  # Quelle unter debian: python3-yaml, sonst pyyaml per pip
except Exception:
    print('''Fehler!\nPyYaml muss installiert sein!
        Installiere entweder python3-yaml unter Debian 
        oder pip pyyaml.''')
    exit()


class Y_dict(dict):
    def get_bool(self, key, default=False, accept_char_as_true=""):
        """ gibt IMMER True oder False zurück!
        """
        value = self.get(key, default)
        if isinstance(value, int):
            # beinhaltet bool
            return True if value else False
        if isinstance(value, str) and len(value):
            if value.strip()[0] in "jJyYtT1":
                return True
            if accept_char_as_true and value.strip()[0] in accept_char_as_true:
                return True
        return False

    def get_list_lowered(self, key, default=[]):
        vlist = self.get_list(key, default)
        return [str(x).lower() for x in vlist]

    def get_list(self, key, default=[]):
        """ was immer als value aus dem dict geliefert wurde, wird nun als Liste zurückgegeben
        """
        value = self.get(key, default)
        # print(f'get_list({key})={value} default={default}')
        if isinstance(value, list):
            return value
        elif value:
            return [str(value)]
        elif isinstance(default, list):
            return default      # Dummywert
        else:
            return [default]


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
                        try:
                            yaml_dict = yaml.safe_load(yaml_block)
                        except Exception as e:
                            yaml_dict = {}
                            print(f'Yaml-Load-Error: Exception {e}')
                        return valid_Y_dict(yaml_dict)
                        
                elif reading_yaml: 
                    yaml_block += line
    except Exception:
        pass                # nicht lesbar = nicht interessant...

    return valid_Y_dict("")
    
    
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
    return valid_Y_dict(yaml_dict)


def valid_Y_dict(yaml_dict):
    if not isinstance(yaml_dict, dict):
        return Y_dict({"m²_yaml_load_error": True}) 
    return Y_dict(yaml_dict)
    