""" debug druckt ggf.
            first: param1, param2
    aus
"""


def debug(c_o, first, *params):
    params_seperator = ""
    if c_o.flag_verbose:
        output = str(first)
        if params:
            output += ": "
            for p in params:
                output += params_seperator + str(p)
                params_seperator = ", "

        print(output)


DEMO_MDM_DIR_YAML = """
## mdm_dir.yaml
## Enthält 2 Informationsblöcke für die Sidebars und die sitemap

## 1. Info zu diesem Verzeichnis
##      Wird für sidebar des Elternverzeichnisses oder als root in Kindverzeichnissen ausgewertet
##
##      indexfilename: xyz.html
##          als Alternative zur index.html
##
#m²_indexfilename: demo.html
##
##      overridetitle: Demoinhalte
##          Eigentlich sollte der Verzeichnistitel der Datei indexfilename entnommen werden.
##          Dies kann hier übersteuert werden (kann inkonsistent wirken)
#m²_overridetitle: Demoinhalte
##
##      subdirprio: High oder Low
##          Wird damit in der sidebar des übergeordneten Verzeichnisses einsortiert.
##          Dort werden High/normal/Low in drei Blöcken, jeweils in sich alphabetisch sortiert
##          angeordnet im Format Fett/normal/kursiv.
#m²_subdirprio: Low
##      

## 2. Linklisten
##      links ist ein array of dicts (welche link, title und hover als keys enthalten).
##          * Die Links werden am Ende der Sidebar als einzelne Links aufgeführt.
##          * title ist der Anzeigename
##          * hover wird angezeigt, wenn die Maus über den Link gleitet.
##          Sichtbarkeit: Sie sind also neben jeder Seite dieses Verzeichnisses sichtbar
##          Anzahl: Kein Limit...
##
#m²_links:
#    - link:  'http://example.com'
#      title: 'Example-homepage'
#    - link:  'https://www.google.com'
#      title: 'Let's Search something'
#      hover: 'go to google'
##
"""


def write_demo_mdm_dir_yaml(path):
    le_path = path / "mdm_dir.yaml.blank"
    with open(le_path, 'w') as f:
        f.write(DEMO_MDM_DIR_YAML)
    return str(le_path)


DEMO_MDM_ROOT_YAML = """
## mdm_root.yaml
## Enthält Informationen für den gesamten Verzeichnisbaum, beginnend mit dem Verzeichnis, in dem die Datei liegt.
## Es handelt sich quasi um die Konfigurationsdatei der mdmachine.
## 
## Beispielinhalte sind einfach auskommentiert.
##
## 1. Klassisches Customizing
##
##      m²_lang: Sprachstring
##          welche Sprache soll als HTML lang Wert gesetzt werden.
##          Wert im Markdown-YAML-Block überschreibt dies.
m²_lang: "de-DE"

## 1.2. Liste von einzubindenden Dateien
##      Hier nur nach Zweck unterschieden. Wenn weitere benötigt werden, dann mit @include einbinden
##
##      Für jede HTML-Datei
m²_cssfile_main: 'https://www.bienmueller.de/css/cb.css'
##      Für aus md generierte zusätzlich zu main
m²_cssfile_md: 'https://www.bienmueller.de/css/cb_md.css'
##      Für in mdmachine generierte (Sidebar, Sitemap) zusätzlich zu main
m²_cssfile_sb: 'https://www.bienmueller.de/css/cb_sb.css'

## Der wichtigste Font (im woff2-Format), der vorab geladen werden soll
m²_mainfont: 'https://www.bienmueller.de/fonts/RadioCanadaRegular.woff2'

## Eine Liste von in allen Markdowndateien einzubindende Styles
#m²_include_style: demo
#m²_include_style: [demo, schule]

## 2. Fix-Link-Liste
##    Diese Links werden in jede Sidebar übernommen, sind also überall präsent
m²_fixlinks:
    - link: 'https://bienmueller.de'
      title: 'Homepage C.B.'
    - link: 'https://tabula.info'
      title: 'Public Displays'
      
    
## 3. Flags 
##
## Soll im root-Verzeichenis ("hier") eine sitemap.html erzeugt werden?
m²_generate_sitemap: True

## 
"""

def write_demo_mdm_root_yaml(path):
    le_path = path / "mdm_root.yaml.blank"
    with open(le_path, 'w') as f:
        f.write(DEMO_MDM_DIR_YAML)
    return str(le_path)
        
