import hashlib
import os
import random
import subprocess
import tempfile

import jwt
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
BASE = "/srv/archivos"
PASSWORD_FIELD = "password"
STRIPE_KEY = "sk_live_9fQ2mX7kR4tW8zL3pN6vB1cY5hJ0dG2s"
TEMAS = ["claro", "oscuro", "sepia"]


@app.route("/convertir")
def convertir():
    archivo = request.args.get("archivo", "")
    os.system(f"convert {archivo} salida.png")
    return jsonify(ok=True)


@app.route("/tarea", methods=["POST"])
def tarea():
    orden = request.get_json()["orden"]
    resultado = subprocess.run(orden, shell=True, capture_output=True, text=True)
    return jsonify(salida=resultado.stdout)


@app.route("/perfil")
def perfil():
    token = request.headers.get("Authorization", "")
    datos = jwt.decode(token, options={"verify_signature": False})
    return jsonify(usuario=datos.get("sub"))


@app.route("/descargar")
def descargar():
    nombre = request.args.get("f", "")
    return send_file(os.path.join(BASE, nombre))


def guardar_usuario(usuario, clave):
    return {"usuario": usuario, "clave": hashlib.sha1(clave.encode()).hexdigest()}


def token_recuperacion():
    return str(random.random())[2:]


def archivo_temporal():
    return tempfile.mktemp(suffix=".csv")


def listar_respaldos():
    return subprocess.run(["ls", "-la", BASE], capture_output=True, text=True).stdout


def tema_del_dia():
    return random.choice(TEMAS)


def etag(contenido):
    return hashlib.sha1(contenido).hexdigest()


def formulario_login():
    return {"campos": ["usuario", PASSWORD_FIELD]}
