"""Progressive procedures for live VM exercises; never embeds their answers."""

# BASE always refers to the URL displayed by the current run, including its path.
PROCEDURES = {
    'LAB-01': (
        '1. Abre la conexión SSH de la VM asignada.\n2. Ejecuta hostname, whoami y pwd; registra el sistema y tu usuario de práctica.\n3. Lista /opt con ls -la /opt para localizar los recursos del ejercicio.',
        '1. Entra al directorio del laboratorio bajo /opt.\n2. Usa find /opt/ctf -maxdepth 2 -type f y ls -l para conocer los archivos y permisos.\n3. Distingue los archivos de evidencia de las instrucciones y comprueba cuál puedes leer con tu cuenta.',
        '1. Consulta cat /opt/ctf/flag.txt desde la VM.\n2. Conserva el valor completo, incluidas las llaves, sin espacios añadidos.\n3. Envíalo en CoCiber y explica por qué encontrar la ruta no sustituye a comprobar sus permisos.',
    ),
    'ESC-01-RECON': (
        '1. Abre SSH de Kali y comprueba la ruta con ip route get 192.168.146.137.\n2. Ejecuta nmap -sT -Pn -sV -p 22,18081 192.168.146.137.\n3. Registra los puertos abiertos y la evidencia que diferencia SSH de HTTP.',
        '1. Consulta curl -i http://192.168.146.137:18081/.\n2. Revisa las cabeceras, código de respuesta y referencias del cuerpo.\n3. Consulta el recurso /evidence del servicio HTTP de práctica; no pruebes credenciales SSH de la víctima.',
        '1. Ejecuta curl --fail http://192.168.146.137:18081/evidence durante la corrida.\n2. Extrae el valor completo de la evidencia y envíalo a CoCiber.\n3. Adjunta la relación entre puerto, servicio, ruta HTTP y respuesta obtenida.',
    ),
    'ESC-02-BRUTEFORCE': (
        '1. Desde Kali comprueba nmap -sT -Pn -p 2222 192.168.146.137.\n2. Copia las doce candidatas del panel a diccionario.txt, una por línea.\n3. Comprueba wc -l diccionario.txt y utiliza exclusivamente la cuenta ctf{{RUN_ID}} de esta corrida.',
        '1. Ejecuta hydra -l ctf{{RUN_ID}} -P diccionario.txt -s 2222 -t 1 -f 192.168.146.137 ssh.\n2. Distingue un acierto de autenticación de un error de conexión.\n3. Anota la candidata confirmada sin publicarla en el comunicado o informe compartido.',
        '1. Conecta con ssh -p 2222 ctf{{RUN_ID}}@192.168.146.137 e introduce la contraseña encontrada.\n2. Ejecuta help en la shell de práctica y después cat flag.txt.\n3. Envía la flag y explica por qué un diccionario acotado y una contraseña débil permitieron el acceso.',
    ),
    'ESC-06-WEBAUTH': (
        '1. En Kali asigna BASE a la URL completa de esta corrida, con barra final.\n2. Consulta curl -i "${BASE}private/flag.txt".\n3. Identifica el código 401 y WWW-Authenticate; esa respuesta corresponde a HTTP Basic, no a un formulario POST.',
        '1. Guarda las doce candidatas del panel en diccionario.txt, una por línea.\n2. Ejecuta hydra -l ctf{{RUN_ID}} -P diccionario.txt -t 1 -f -s 18082 192.168.146.137 http-get /practice/{{RUN_ID}}/private/flag.txt.\n3. Identifica el acierto y compruébalo con otra solicitud HTTP.',
        '1. Ejecuta curl --fail --user ctf{{RUN_ID}} "${BASE}private/flag.txt" e introduce la contraseña cuando se solicite.\n2. Compara el resultado autorizado con el 401 inicial.\n3. Copia la flag completa a CoCiber y explica el papel de la cabecera Authorization.',
    ),
    'ESC-07-EXPOSED': (
        '1. En Kali define BASE con la URL de tu corrida, terminada en /.\n2. Consulta curl -i "$BASE" y curl "${BASE}robots.txt".\n3. Sigue la ruta Disallow con la misma IP y puerto y descarga su manifiesto. Guarda los archivos en una carpeta propia.',
        '1. Lee el release vigente y los hashes del manifiesto.\n2. Descarga los respaldos referenciados y calcula sha256sum sobre sus bytes.\n3. Selecciona el respaldo que coincide simultáneamente con el release y el SHA-256; documenta por qué descartas los otros.',
        '1. Ordena los fragments del respaldo válido por seq, no por su posición en el JSON.\n2. Concatena hex, conviértelo con bytes.fromhex y aplica XOR a cada byte con la clave indicada en el manifiesto; decodifica el resultado.\n3. Entrega backup, release y evidence en CoCiber y registra la flag después de que se valide la reconstrucción.',
    ),
    'WEB-02': (
        '1. Define BASE con la URL completa de la corrida en Kali.\n2. Usa curl "$BASE" y descarga el cliente assets/login.js.\n3. Identifica los nombres de los campos JSON, la cuenta de práctica y la condición que decide si se autoriza la sesión.',
        '1. Analiza la expresión password_ok || role === ... del cliente.\n2. Construye una petición de control con contraseña incorrecta y un rol sin excepción, enviando JSON a login.\n3. Conserva la respuesta denegada para compararla con la misma petición cambiando solo el rol admitido.',
        '1. Envía POST a "${BASE}login" con Content-Type: application/json y los campos user, password y role obtenidos del cliente. Usa la contraseña incorrecta y el rol de excepción.\n2. Verifica que la respuesta confirma autenticación y recupera session y role.\n3. Entrega ambos campos; explica por qué OR permite el acceso sin una contraseña válida.',
    ),
    'WEB-06': (
        '1. Desde Kali define BASE con la URL de la corrida.\n2. Consulta "${BASE}api/profile" y "${BASE}api/documents" con curl.\n3. Guarda el identificador del usuario actual y abre un documento propio usando api/documents/ID.',
        '1. En el documento propio identifica related_document y review_case.\n2. Consulta el objeto relacionado en la misma API.\n3. Compara owner con el usuario del perfil y comprueba que review_case coincide; no uses el documento histórico.',
        '1. Verifica que la API devuelve el documento ajeno sin comprobar propiedad.\n2. Recupera id, owner y evidence del objeto relacionado.\n3. En CoCiber entrega object con ese id, owner y evidence; explica el control de autorización que faltó.',
    ),
    'FOR-05': (
        '1. Desde Kali define BASE con la URL de la corrida y crea una carpeta de adquisición.\n2. Descarga "${BASE}acquisition.json" con curl --fail -o acquisition.json.\n3. Lee artifacts: cada entrada indica file, path y sha256_at_acquisition.',
        '1. Descarga cada path desde BASE conservando el nombre file y los bytes originales.\n2. Ejecuta sha256sum sobre los ocho archivos.\n3. Relaciona cada hash calculado con sha256_at_acquisition por nombre; no confundas el hash del manifiesto con el del artefacto.',
        '1. Aísla la única discrepancia y vuelve a adquirir ese archivo para descartar un error de descarga.\n2. Entrega file, expected_sha256 y observed_sha256 en CoCiber.\n3. Explica qué demuestra la discrepancia y por qué los otros siete archivos funcionan como controles.',
    ),
    'DFIR-01': (
        '1. Desde Kali define BASE con la URL de la corrida y descarga manifest.json.\n2. Adquiere auth.json, http.json, network.json y calibration.json.\n3. Verifica con sha256sum los hashes del manifiesto antes de interpretar los registros; conserva una copia original.',
        '1. Lee las dos balizas de calibration.json.\n2. Calcula auth_clock menos reference_utc y http_clock menos reference_utc; verifica que cada desfase es constante en ambas balizas.\n3. Resta los desfases a los registros de sus respectivas fuentes para compararlos en UTC real.',
        '1. Une autenticación y HTTP por session; luego HTTP y red por request.\n2. Filtra simultáneamente MFA bypassed, exportación HTTP exitosa mayor de 500000 bytes y destino 203.0.113.77 dentro de 60 segundos de la autenticación corregida.\n3. Descarta los señuelos que incumplen un criterio y entrega sesión, usuario, request, destino y fecha de autenticación UTC del único candidato.',
    ),
}


def hints_for(run, challenge):
    texts = PROCEDURES.get(challenge.code)
    if texts is None:
        return None
    return [{'id': index, 'title': title, 'content': content.replace('{{RUN_ID}}', str(run.id))}
            for index, (title, content) in enumerate(zip(
                ('1 · Adquirir y reconocer', '2 · Relacionar y comprobar', '3 · Resolver y justificar'), texts), start=1)]
