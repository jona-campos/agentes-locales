# Informe de seguridad: fixtures/vulnerable

Fecha: 2026-11-07T22:03:01 · Modelo: qwen2.5-coder:7b

| Resultado | Cantidad |
|---|---|
| Reales | 15 |
| Dudosos | 0 |
| Sin revisar | 0 |
| Falsos positivos (según el modelo) | 3 |
| Paquetes con vulnerabilidades | 6 |

> El veredicto del modelo es una sugerencia: revisa siempre el hallazgo original.

## Reales

### [ALTA] app.py:19-20

**Explicación:** La función 'execute' de 'db' recibe una consulta SQL formada con datos del usuario, lo que permite una inyección SQL.

**Arreglo:** Reemplazar la consulta SQL con una consulta parametrizada. Por ejemplo:
`filas = db.execute('SELECT * FROM productos WHERE nombre = ?', (nombre,)).fetchall()`

- `semgrep sql-injection-db-cursor-execute`: User-controlled data from a request is passed to 'execute()'. This could lead to a SQL injection and therefore protected information could be leaked. Instead, use django's QuerySets, which are built …
- `bandit B608`: Possible SQL injection vector through string-based query construction.
- `semgrep formatted-sql-query`: Detected possible formatted SQL query. Use parameterized queries instead.
- `semgrep sqlalchemy-execute-raw-query`: Avoiding SQL string concatenation: untrusted input concatenated with raw SQL query can result in SQL Injection. In order to execute raw query safely, prepared statement should be used. SQLAlchemy pro…
- `semgrep tainted-sql-string`: Detected user input used to manually construct a SQL string. This is usually bad practice because manual construction could accidentally result in a SQL injection. An attacker could use a SQL injecti…
- `semgrep tainted-sql-string`: Detected user input used to manually construct a SQL string. This is usually bad practice because manual construction could accidentally result in a SQL injection. An attacker could use a SQL injecti…

### [ALTA] app.py:26-27

**Explicación:** La función 'eval' ejecuta dinámicamente el código proporcionado por el usuario, lo que puede llevar a la ejecución de código arbitrario y potencialmente dañino.

**Arreglo:** Reemplazar 'eval' con una función segura para evaluar expresiones matemáticas, como 'ast.literal_eval' para expresiones simples o usar una biblioteca específica para el cálculo matemático.

- `semgrep user-eval`: Found user data in a call to 'eval'. This is extremely dangerous because it can enable an attacker to execute arbitrary remote code on the system. Instead, refactor your code to not use 'eval' and in…
- `bandit B307`: Use of possibly insecure function - consider using safer ast.literal_eval.
- `semgrep eval-injection`: Detected user data flowing into eval. This is code injection and should be avoided.
- `semgrep eval-detected`: Detected the use of eval(). eval() can be dangerous if used to evaluate dynamic content. If this content can be input from outside the program, this may be a code injection vulnerability. Ensure eval…

### [ALTA] app.py:33

**Explicación:** La función 'subprocess.check_output' se utiliza con 'shell=True', lo que permite la ejecución de comandos shell proporcionados por el usuario. Esto puede llevar a una inyección de comandos.

**Arreglo:** Reemplazar 'shell=True' por una lista de argumentos para evitar la inyección de comandos. Por ejemplo: `subprocess.check_output(['ping', '-n', '1', host])`.

- `bandit B602`: subprocess call with shell=True identified, security issue.
- `semgrep subprocess-injection`: Detected user input entering a `subprocess` call unsafely. This could result in a command injection vulnerability. An attacker could use this vulnerability to execute arbitrary commands on the host, …
- `semgrep dangerous-subprocess-use-audit`: Detected subprocess function 'check_output' without a static string. If this data can be controlled by a malicious actor, it may be an instance of command injection. Audit the use of this call to ens…
- `semgrep dangerous-subprocess-use`: Detected subprocess function 'check_output' with user controlled data. A malicious actor could leverage this to perform command injection. You may consider using 'shlex.escape()'.
- `semgrep subprocess-shell-true`: Found 'subprocess' function 'check_output' with 'shell=True'. This is dangerous because this call will spawn the command using a shell process. Doing so propagates current shell settings and variable…

### [ALTA] app.py:39

**Explicación:** La función `pickle.loads` y `yaml.load` deserializan datos proporcionados por el usuario, lo que puede permitir la ejecución de código arbitrario si los datos son manipulados por un atacante.

**Arreglo:** Reemplazar `pickle.loads` por `json.loads` y `yaml.load` por `yaml.safe_load` para evitar la deserialización de datos no confiables.

- `bandit B301`: Pickle and modules that wrap it can be unsafe when used to deserialize untrusted data, possible security issue.
- `semgrep insecure-deserialization`: Detected the use of an insecure deserialization library in a Flask route. These libraries are prone to code execution vulnerabilities. Ensure user data does not enter this function. To fix this, try …
- `semgrep avoid-pickle`: Avoid using `pickle`, which is known to lead to code execution vulnerabilities. When unpickling, the serialized data could be manipulated to run arbitrary code. Instead, consider serializing the rele…

### [ALTA] app.py:45

**Explicación:** La función 'yaml.load' deserializa datos proporcionados por el usuario, lo que puede permitir la ejecución de código arbitrario si el contenido de la petición POST contiene objetos maliciosos. Es recomendable usar 'yaml.safe_load' en su lugar.

**Arreglo:** Reemplazar 'config = yaml.load(request.get_data())' por 'config = yaml.safe_load(request.get_data())'

- `bandit B506`: Use of unsafe yaml load. Allows instantiation of arbitrary objects. Consider yaml.safe_load().
- `semgrep insecure-deserialization`: Detected the use of an insecure deserialization library in a Flask route. These libraries are prone to code execution vulnerabilities. Ensure user data does not enter this function. To fix this, try …

### [ALTA] app.py:51

**Explicación:** La función requests.get() se llama con una URL fija, pero el método verify=False desactiva la verificación del certificado SSL, lo que puede permitir ataques man-in-the-middle.

**Arreglo:** Reemplazar 'verify=False' por 'verify=True' para activar la verificación del certificado SSL.

- `bandit B501`: Call to requests with verify=False disabling SSL certificate checks, security issue.
- `bandit B113`: Call to requests without timeout
- `semgrep use-raise-for-status`: There's an HTTP request made with requests, but the raise_for_status() utility method isn't used. This can result in request errors going unnoticed and your code behaving in unexpected ways, such as …
- `semgrep use-timeout`: Detected a 'requests' call without a timeout set. By default, 'requests' calls wait until the connection is closed. This means a 'requests' call without a timeout will hang the program if a response …
- `semgrep disabled-cert-validation`: Certificate verification has been explicitly disabled. This permits insecure connections to insecure servers. Re-enable certification validation.

### [ALTA] app.py:58

**Explicación:** La contraseña se compara directamente con un valor MD5 en el código, lo que es inseguro.

**Arreglo:** Reemplazar la función MD5 con una función de hash segura como scrypt.

- `bandit B324`: Use of weak MD5 hash for security. Consider usedforsecurity=False
- `bandit B324`: Use of weak MD5 hash for security. Consider usedforsecurity=False
- `semgrep insecure-hash-algorithm-md5`: Detected MD5 hash algorithm which is considered insecure. MD5 is not collision resistant and is therefore not suitable as a cryptographic signature. Use SHA256 or SHA3 instead.
- `semgrep insecure-hash-algorithm-md5`: Detected MD5 hash algorithm which is considered insecure. MD5 is not collision resistant and is therefore not suitable as a cryptographic signature. Use SHA256 or SHA3 instead.
- `semgrep md5-used-as-password`: It looks like MD5 is used as a password hash. MD5 is not considered a secure password hash because it can be cracked by an attacker in a short amount of time. Use a suitable password hashing function…

### [ALTA] app.py:65

**Explicación:** La llamada a 'subprocess.check_output' con 'shell=True' permite la inyección de comandos, lo que puede ser utilizado por un atacante para ejecutar comandos arbitrarios en el sistema.

**Arreglo:** Reemplazar la llamada a 'subprocess.check_output' con 'shell=True' por una llamada más segura que no use 'shell=True'. Por ejemplo, usar 'subprocess.run' con argumentos de lista en lugar de una cadena de comandos.

- `bandit B607`: Starting a process with a partial executable path
- `bandit B602`: subprocess call with shell=True seems safe, but may be changed in the future, consider rewriting without shell

### [ALTA] app.py:71

**Explicación:** El uso de MD5 para calcular huellas de archivos es inseguro porque no es resistente a colisiones. Debe reemplazarse por SHA256 o SHA3.

**Arreglo:** Reemplazar `hashlib.md5(f.read()).hexdigest()` por `hashlib.sha256(f.read()).hexdigest()`.

- `bandit B324`: Use of weak MD5 hash for security. Consider usedforsecurity=False
- `semgrep insecure-hash-algorithm-md5`: Detected MD5 hash algorithm which is considered insecure. MD5 is not collision resistant and is therefore not suitable as a cryptographic signature. Use SHA256 or SHA3 instead.

### [ALTA] app.py:75

**Explicación:** El valor de 'host' y 'debug' se obtienen de la ejecución del script, por lo que un atacante podría controlar estos valores si ejecuta el script de una manera no segura.

**Arreglo:** Desactivar el modo de depuración y limitar el host a '127.0.0.1' o 'localhost'. Por ejemplo: `app.run(host='127.0.0.1', debug=False)`.

- `bandit B201`: A Flask app appears to be run with debug=True, which exposes the Werkzeug debugger and allows the execution of arbitrary code.
- `bandit B104`: Possible binding to all interfaces.
- `semgrep avoid_app_run_with_bad_host`: Running flask app with host 0.0.0.0 could expose the server publicly.
- `semgrep debug-enabled`: Detected Flask app with debug=True. Do not deploy to production with this flag enabled as it will leak sensitive information. Instead, consider using Flask configuration variables or setting 'debug' …

### [ALTA] config.py:4

**Explicación:** El valor de ADMIN_PASSWORD es una cadena fija escrita en el código, lo que es un riesgo potencial.

**Arreglo:** Reemplazar la cadena fija con una variable de entorno o una configuración segura.

- `bandit B105`: Possible hardcoded password: '[oculto]'

### [ALTA] config.py:5

**Explicación:** Estos valores son secretos sensibles que deberían almacenarse fuera del código fuente, por ejemplo, en variables de entorno o en un almacén seguro de secretos.

**Arreglo:** Reemplazar los valores literales con variables de entorno o una referencia a un almacén seguro de secretos.

- `semgrep aws-access-token`: A gitleaks aws-access-token was detected which attempts to identify hard-coded credentials. It is not recommended to store credentials in source-code, as this risks secrets being leaked and used by e…
- `semgrep detected-aws-access-key-id-value`: AWS Access Key ID Value detected. This is a sensitive credential and should not be hardcoded here. Instead, read this value from an environment variable or keep it in a separate, private file.

### [ALTA] config.py:6

**Explicación:** La clave secreta AWS_SECRET_ACCESS_KEY está escrita directamente en el código, lo que la hace vulnerable a ser descubierta y utilizada por un atacante.

**Arreglo:** Reemplazar la clave secreta con una variable de entorno o una configuración segura que no esté codificada en el código fuente.

- `gitleaks generic-api-key`: Detected a Generic API Key, potentially exposing access to various services and sensitive operations.
- `bandit B105`: Possible hardcoded password: '[oculto]'
- `semgrep detected-aws-secret-access-key`: AWS Secret Access Key detected

### [ALTA] config.py:7

**Explicación:** El token de GitHub es un secreto que debe almacenarse de forma segura, no en el código fuente.

**Arreglo:** Elimina el token de GitHub del código y almacénalo en una variable de entorno o en un archivo de configuración seguro.

- `gitleaks github-pat`: Uncovered a GitHub Personal Access Token, potentially leading to unauthorized repository access and sensitive content exposure.
- `bandit B105`: Possible hardcoded password: '[oculto]'
- `semgrep generic-api-key`: A gitleaks generic-api-key was detected which attempts to identify hard-coded credentials. It is not recommended to store credentials in source-code, as this risks secrets being leaked and used by ei…
- `semgrep github-pat`: A gitleaks github-pat was detected which attempts to identify hard-coded credentials. It is not recommended to store credentials in source-code, as this risks secrets being leaked and used by either …

### [MEDIA] static/app.js:3

**Explicación:** La función `innerHTML` está siendo utilizada con datos del usuario, lo que puede permitir inyección de código HTML.

**Arreglo:** Reemplazar `innerHTML` por `textContent` para evitar la inyección de código HTML.

- `semgrep insecure-document-method`: User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities
- `semgrep insecure-innerhtml`: User controlled data in a `document.getElementById("saludo").innerHTML` is an anti-pattern that can lead to XSS vulnerabilities

## Falsos positivos (según el modelo)

<details><summary>Ver 3</summary>

### [BAJA] app.py:3

**Explicación:** El import solo de pickle no ejecuta nada peligroso.

- `bandit B403`: Consider possible security implications associated with pickle module.

### [BAJA] app.py:5

**Explicación:** El import solo de 'subprocess' no ejecuta nada peligroso. No se puede determinar si el uso futuro de 'subprocess' es seguro o no.

- `bandit B404`: Consider possible security implications associated with the subprocess module.

### [BAJA] app.py:66

**Explicación:** El uso de eval('2 + 2') no es peligroso porque no evalúa ninguna entrada del usuario.

- `bandit B307`: Use of possibly insecure function - consider using safer ast.literal_eval.

</details>

## Dependencias con vulnerabilidades conocidas

| Paquete | Archivo | Severidad | Vulnerabilidades |
|---|---|---|---|
| certifi@2026.7.22 | requirements.txt | alta | PYSEC-2026-4320 |
| flask@0.12.2 | requirements.txt | alta | PYSEC-2018-66, PYSEC-2019-179, PYSEC-2023-62, PYSEC-2026-2151 |
| pyyaml@5.3.0 | requirements.txt | alta | PYSEC-2020-96, PYSEC-2021-142 |
| requests@2.19.1 | requirements.txt | alta | PYSEC-2018-28, PYSEC-2023-74, PYSEC-2026-1872, PYSEC-2026-1873, PYSEC-2026-2275 |
| urllib3@1.23.0 | requirements.txt | alta | PYSEC-2019-132, PYSEC-2019-133, PYSEC-2026-141, PYSEC-2026-1994, PYSEC-2026-1995, PYSEC-2026-1996, PYSEC-2026-1999, PYSEC-2026-4177, GHSA-g4mx-q9vg-27p4, GHSA-gwvm-45gx-3cf8, GHSA-v845-jxx5-vc9f, GHSA-wqvq-5m8c-6g24 |
| idna@2.7.0 | requirements.txt | media | PYSEC-2026-215, GHSA-jjg7-2v4v-x38h |
