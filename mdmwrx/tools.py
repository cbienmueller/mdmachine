# Batteries

from time import sleep

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


def alte_Dateien_vorhanden(path, poll_gen):
    for oldfile in path.iterdir():
        if oldfile.is_file() and oldfile.stem.startswith(f"_mdm_old-{poll_gen}_"):
            return True
    return False


def alte_Dateien_entfernen(path, poll_gen=0, do_recursive=False, remove_temps=False):
    """poll_gen ist die löschende poll-Generation. Bei Wert null werden alle alten gelöscht! """
    temp_counter = 0
    anycounter, nextcounter = 0, 0
    for oldfile in path.iterdir():
        if oldfile.is_file() and oldfile.stem.startswith("_mdm_old"):
            if (not poll_gen) or oldfile.stem.startswith(f"_mdm_old-{poll_gen}_"):
                print(f"    remove {oldfile.name}")
                oldfile.unlink(missing_ok=True)
                anycounter += 1
            elif oldfile.stem.startswith(f"_mdm_old-{poll_gen + 1}_"):
                nextcounter += 1
        elif remove_temps and oldfile.is_file() and oldfile.stem.startswith("_mdmtemp_"):
            oldfile.unlink(missing_ok=True)
            temp_counter += 1
        elif do_recursive and oldfile.is_dir():
            ac, nc = alte_Dateien_entfernen(oldfile, force_all, do_recursive)
            anycounter += ac
            nextcounter += nc
    if temp_counter:
        print(f'{temp_counter} temporäre Dateien gelöscht.')
    return anycounter, nextcounter


def warte_entferne_exit(startpath, poll_gen=0):
    try:
        sleep(15)
    except KeyboardInterrupt:
        print("Abbruch ok, lösche noch schnell...")
    alte_Dateien_entfernen(startpath, poll_gen)
    exit(0)


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
## Achtung: Änderungen in der Datei werden nur bei einem Neustart von mdmachine eingelesen. 
##          Läuft es dauerhaft mit "-p" (polling) so bemerkt es die Änderung nicht selbst!
##
## Beispielinhalte sind im Foilgenden einfach auskommentiert, da es die Standardwerte sind.
##
## 1. Klassisches Customizing
##
##      m²_lang: Sprachstring
##          welche Sprache soll als HTML lang Wert gesetzt werden.
##          Wert im Markdown-YAML-Block überschreibt dies.
# m²_lang: "de-DE"

## 2a. Liste von einzubindenden URLs
##      Hier nur nach Zweck unterschieden. Wenn weitere benötigt werden, dann mit @include einbinden
##      Oder lokal mit m²_include_css (s.u.). 
##
##      Für jede HTML-Datei
# m²_cssfile_main: 'https://www.bienmueller.de/css/mdm_main.css'
##      Für aus md generiertes zusätzlich zu main
# m²_cssfile_md: 'https://www.bienmueller.de/css/mdm_md.css'
##      Für in mdmachine generierte (Sidebar, Sitemap, Timeline) zusätzlich zu main
# m²_cssfile_sb: 'https://www.bienmueller.de/css/mdm_sb.css'
##
##      Der wichtigste Font (im woff2-Format), der vorab geladen werden soll
# m²_mainfont: 'https://www.bienmueller.de/fonts/OpenSansRegular.woff2'

## 2b. Eine Liste von in allen Markdowndateien einzubindende Styles
##     Styles liegen im Pfad von mdmachine
##          Beispiele (Standard: nichts):
##          Ein Style:
## m²_include_style: demo
##          Array of Styles:
## m²_include_style: [demo, schule]
## 
## 2c. Liste von CSS-Datei-Pfaden relativ zum Root, die als File-URLs eingebunden werden.
##
## m²_include_css: ["css/design.css"]
# m²_include_css: []
##
## 2d. Eine CSS-Datei, die aber auch bei sidebat, sitemap und timeline inkludiert werden soll
##     Dies ist der Ort für einheitliche Farbdefinitionen
##
# m²_include_main_css: ""
##
## 3. Fix-Link-Liste
##    Diese Links werden in jede Sidebar übernommen, sind also überall präsent.
##    Hier nur ein Beispiel mit zwei Links, da der Standardwert leer ist:
## m²_fixlinks:
##    - link: 'https://bienmueller.de'
##      title: 'Homepage C.B.'
##    - link: 'https://tabula.info'
##      title: 'Public Displays'
##      hover: Klick mich!
##
    
## 4a. Flags 
##
## Soll im root-Verzeichenis ("hier") eine sitemap.html erzeugt werden?
# m²_generate_sitemap: False
# m²_generate_sidebar: False
# m²_verbose: False


## 4b. Flags, die nur zum Tragen kommen, wenn in einer md-Datei dieses Flag nicht gesetzt wird
# m²_suppress_pdf: False
# m²_generate_slides: False
## 
"""


def write_demo_mdm_root_yaml(path):
    le_path = path / "mdm_root.yaml.blank"
    with open(le_path, 'w') as f:
        f.write(DEMO_MDM_ROOT_YAML)
    return str(le_path)
        
