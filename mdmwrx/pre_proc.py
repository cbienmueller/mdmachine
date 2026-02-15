#!/bin/python3


"""preprocess
    ergänzt markdown-Quelltext mit Formatierungen, welche z.B. die Sprache beinhalten.
    Codeblöcke der Klasse .execute werden beim Durchreichen außerdem  "ausgeführt":

        * Python- und Java-Code wird tatsächlich ausgeführt und 
            die Ausgabe als "Resultat" in einem eigenen Codeblock eingefügt.

        * Markdown und HTML wird nur in einem Output-Div wiedergegeben und
            damit vom Browser "ausgeführt".
        
        * Mermaid-Diagramme werden NICHT mehr im Quelltext angezeigt, sondern im Browser nur über externes Javascript
            in ein Diagramm konvertiert.

"""

import sys
import subprocess
import pickle
import datetime

from io import StringIO
from hashlib import blake2b

EASYPRINT_JAVA = \
    """
void print(String value)    { System.out.print(value); }
void print(long value)      { System.out.print(value); }
void print(double value)    { System.out.print(value); }
void print(boolean value)   { System.out.print(value); }
void print(char value)      { System.out.print(value); }
void print(char[] value)    { System.out.print(value); }
void print()                { System.out.print(""); }
void println(String value)  { System.out.println(value); }
void println(long value)    { System.out.println(value); }
void println(double value)  { System.out.println(value); }
void println(boolean value) { System.out.println(value); }
void println(char value)    { System.out.println(value); }
void println(char[] value)  { System.out.println(value); }
void println()              { System.out.println(""); }

"""

LAST_JAVA_EXECUTES_FILENAME = '/tmp/mdm_java_executes.pickle'

last_java_executes: dict[str, str] = {}  # nimmt hash und output von Code auf
last_java_executes_filled: bool = False
last_java_executes_loaded: bool = False    # auch erfolglose loads zählen

MERMAID_LOADER = \
    '''\n\n\n
<!-- Wegen eines Mermaid-Diagramms wird das folgende Modul am Ende eingebunden -->
<script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11.9.0/dist/mermaid.esm.min.mjs";
    var org_url="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    var nAgt = navigator.userAgent;
    if (nAgt.indexOf("Firefox")!=-1) {
    var config = { startOnLoad: true}; 
    console.log("Firefox erkannt" + nAgt);}
    else {
    var config = { startOnLoad: true, securityLevel: "sandbox" };
    console.log("Kein Firefox erkannt" + nAgt);
    }
    mermaid.initialize(config);
</script>\n
'''
#  ##  Anmerkung: obige Adresse enthält fest kodiert die Version von Mermaid. 
#      Wenn diese nicht mehr verfügbar ist haben wir ein Problem...
#  ##  Grund: die Versionen 11.10 - 10.12 (gerade aktuell) haben einen Bug beim Sandbox-Modus.


def preprocess(filein, fileout, remove_yaml=False):
    global last_java_executes
    global last_java_executes_filled
    
    exec_env = {}
    code_marker = ''  # gefundene Backticks, mit denen der Codeblock eröffnet wurde. ''=nicht im Code
    code_block = []   # nimmt zu verarbeitende Codezeilen
    code_typ = ''     # nimmt derzeit Python, Java, HTML oder Markdown auf
    java_store = ''   # nimmt eventuellen Javacode, der gespeichert werden soll, auf
    return_lines = []
    output_lines = []
    yaml_sep_count = 0
    java_easyprint = False
    
    flag_include_mermaid_cdn = False   # soll für ein oder mehrere mermaid-Diagramme die js-Bibliothek geladen werden?
    
    def code_kennzeichen_ist(sprache):
        """ Erkennt die beiden Fälle:
            ```Python
            ```{.pyTHon}
        """
        if (f'.{sprache}' in line.lower()) or (f'```{sprache}' in line.lower()):
            return True
        return False
        
    for line in filein:
        
        # Schritt 1: ggf. YAML-Block am Anfange entfernen (für Verkettung von markdown-Dateien)
        if remove_yaml:
            if line.startswith('---') or line.startswith('...'):
                yaml_sep_count += 1
            if yaml_sep_count == 2:
                remove_yaml = False   # job erfüllt
            if yaml_sep_count > 0:
                line = ""
                
        # Schritt 2a:
        # Ein beginnender Code-Block wird ggf. erkannt und analysiert
        if not code_marker and line.startswith("```"):
            code_marker = "```"   
            while line.startswith(code_marker + "`"):
                code_marker += "`"
            # Nun wird geklärt, ob und wie er danach verarbeitet werden soll
            code_typ = ""
            code_cnt = ""
            do_execute = False
            code_block = [] 
            if '.execute' in line:              # Klasse execute muss dem Codeblock zugeordnet werden, 
                do_execute = True               # damit er hier auch ausgeführt wird
                if '.easyprint' in line:
                    java_easyprint = True
                
            if code_kennzeichen_ist("python"):  # die Klasse python muss dazu dem Codeblock zugeordnet werden
                code_typ = "Python"
                if do_execute:
                    if ".continue" not in line:
                        code_cnt = ''
                        exec_env = {}
                    else:
                        code_cnt = "&nbsp;..."
                        
            elif code_kennzeichen_ist("java"):
                code_typ = "Java"
                if do_execute:
                    if ".continue" not in line: 
                        code_cnt = ''
                        java_store = ''  # auch die Info, ihn nicht zu benutzen
                    else:
                        code_cnt = "&nbsp;..."
                        
            elif code_kennzeichen_ist("markdown"): 
                code_typ = "Markdown"
            elif code_kennzeichen_ist("html"):
                code_typ = "HTML"
            elif code_kennzeichen_ist("mermaid"):
                code_typ = "Mermaid"
            elif code_kennzeichen_ist("code"):    
                code_typ = "Code"		# generischer Code, nicht interpretierbar!

            if code_typ != "Mermaid":   # Nur bei Mermaid wird der gesamte Codeblock anders geschrieben
                return_lines.append(line)
            
            if code_typ == "Markdown":
                code_block.append("\n")  # fixt manche Markdown-Fehlinterpretationen durch zusätzliche Leerzeile davor
 
        # Schritt 2b:
        # laufende Zeilenverarbeitung innerhalb eines Code-Blocks inkl. dessen Ende
        elif code_marker:
            # (fast) immer die Zeile durchreichen, da der Quelltext ja ausgegeben wird
            if code_typ != "Mermaid":
                return_lines.append(line)

            # schon das Ende erreicht?
            if line.startswith(code_marker) and not line.startswith("`" + code_marker):  # Länge muss stimmen!
                code_marker = ''
                # jetzt wurde der Codeblock beendet und daher muss code_block[] ggf. ausgeführt werden
                if code_typ:  # Nur für erkannte Quellcodes
                    if code_typ == "Mermaid":
                        the_code = "".join(code_block)
                        return_lines.append(f'''<pre class="mermaid">\n{the_code}\n</pre>\n''')
                        flag_include_mermaid_cdn = True
                        code_block = []
                        
                    elif do_execute:  # Große Fallunterscheidung :-)

                        if code_typ == "Python":
                            python_output = ''
                            old_stdout = sys.stdout
                            redirected_output = sys.stdout = StringIO()
                            try:
                                exec("".join(code_block), exec_env)
                            except Exception as e:
                                python_output = 'Ausführung fehlgeschlagen: ' + str(e) + '\n\n'
                            finally:                        # !
                                sys.stdout = old_stdout     # !

                            python_output += redirected_output.getvalue()
                            if python_output.strip():
                                output_lines.append('```\n')
                                output_lines.append(python_output)
                                output_lines.append('\n```\n')
                            
                        if code_typ == "Java":
                            the_code = "".join(code_block)
                            # Code ausführen
                            if code_cnt != '' and java_store:
                                java_store += '\n\n' + the_code
                                resultat = execute_java(java_store)
                                resultat = resultat.split('----- javastore trennlinie -----')[-1]
                            else:
                                if java_easyprint:
                                    the_code = EASYPRINT_JAVA + the_code
                                resultat = execute_java(the_code)
                                java_store = the_code
                            # Resultat säubern
                            while resultat.startswith("\n"):
                                resultat = resultat[1:]
                            while resultat.endswith("\n"):
                                resultat = resultat[:-1]
                            # Bei echter Ausgabe für zukünftige Ausgaben einen Trenner einfügen und Resultat ausgeben
                            if resultat:
                                java_store += '\n\nSystem.out.println("\n----- javastore trennlinie -----\n");\n\n' 
                                output_lines.append(f'```\n{resultat}\n```\n')
                            
                        elif code_typ in ("Markdown", "HTML"):
                            code_block.append("\n")  # fixt manche Markdown-Fehlinterpretationen durch Leerzeile danach
                            output_lines.append("".join(code_block))

                        code_block = []
                        # ## 
                        if output_lines:
                            return_lines.append('\n::::: {.m²_output}\n')
                            return_lines += output_lines
                            return_lines.append(':::::\n\n')
                            output_lines = []

            # oh, doch nur eine weitere Code-Zeile, die nur bei Bedarf gespeichert wird
            elif code_typ:
                code_block.append(line)

        # Schritt 2c:
        # oder blindes Durchreichen jeder anderen Zeile
        else:
            return_lines.append(line)
    
    print("".join(return_lines), end='', file=fileout)    
    
    if flag_include_mermaid_cdn:
        print(MERMAID_LOADER,
              file=fileout)
        
    if last_java_executes_filled:
        with open(LAST_JAVA_EXECUTES_FILENAME, 'wb') as fp:
            pickle.dump(last_java_executes, fp, protocol=pickle.HIGHEST_PROTOCOL)
            print("Java_Executes gepickelt...")

    # Ende des Preprocessings    
         
            
def execute_java(thecode):
    global last_java_executes
    global last_java_executes_filled
    global last_java_executes_loaded
    
    thecode += "\n/exit\n"
    
    if not last_java_executes_loaded:
        try:
            with open(LAST_JAVA_EXECUTES_FILENAME, 'rb') as fp:
                last_java_executes = pickle.load(fp)
                print(f"Java_Executes unter {LAST_JAVA_EXECUTES_FILENAME} eingelesen!")
        except Exception:
            last_java_executes = {}
            print(f"Java_Executes unter {LAST_JAVA_EXECUTES_FILENAME} nicht gefunden!")
            
        last_java_executes_loaded = True  # probier's nicht nochmal
        # nicht von heute? löschen!
        if (not last_java_executes) or last_java_executes.get('processing_date', '') != datetime.date.today().isoformat():
            last_java_executes = {}
            last_java_executes['processing_date'] = datetime.date.today().isoformat()
            last_java_executes_filled = True
            print("Evtl. veraltete Java_Executes gelöscht")

    code_hash = blake2b(thecode.encode('utf-8')).hexdigest()
    output = last_java_executes.get(code_hash, "")
    if output:
        print("Java_executes - Treffer!")
        return output
        
    print("Java_executes - unbekannt!")
    
    process = subprocess.Popen(['jshell', '-s', '-'],
                               stdout=subprocess.PIPE, 
                               stdin=subprocess.PIPE, 
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(input=thecode.encode('utf-8'))
    if not stderr:
        output = stdout.decode('utf-8')
    else:
        output = stdout.decode('utf-8') + "\n" + stderr.decode('utf-8')
        
    last_java_executes[code_hash] = output
    last_java_executes_filled = True
    
    return output


def do_pre_proc(file_in, file_out, remove_yaml=False):
    with open(file_in, 'r') as fin:
        with open(file_out, 'w') as fout:
            preprocess(fin, fout, remove_yaml)    
            
            
if __name__ == "__main__":
    print("kein direkter Aufruf mehr!")
