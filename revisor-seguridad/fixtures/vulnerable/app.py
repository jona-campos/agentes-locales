import hashlib
import os
import pickle
import sqlite3
import subprocess

import requests
import yaml
from flask import Flask, request

from config import ADMIN_PASSWORD

app = Flask(__name__)
db = sqlite3.connect("tienda.db", check_same_thread=False)


@app.route("/producto")
def producto():
    nombre = request.args.get("nombre", "")
    filas = db.execute(f"SELECT * FROM productos WHERE nombre = '{nombre}'").fetchall()
    return {"productos": filas}


@app.route("/calcular")
def calcular():
    expresion = request.args.get("expr", "0")
    return {"resultado": eval(expresion)}


@app.route("/ping")
def ping():
    host = request.args.get("host", "localhost")
    salida = subprocess.check_output("ping -n 1 " + host, shell=True)
    return {"salida": salida.decode()}


@app.route("/sesion", methods=["POST"])
def sesion():
    datos = pickle.loads(request.get_data())
    return {"usuario": datos.get("usuario")}


@app.route("/importar", methods=["POST"])
def importar():
    config = yaml.load(request.get_data())
    return {"claves": list(config)}


@app.route("/clima")
def clima():
    r = requests.get("https://api.ejemplo.com/clima", verify=False)
    return r.json()


@app.route("/login", methods=["POST"])
def login():
    clave = request.form.get("clave", "")
    if hashlib.md5(clave.encode()).hexdigest() == hashlib.md5(ADMIN_PASSWORD.encode()).hexdigest():
        return {"ok": True}
    return {"ok": False}, 401


@app.route("/version")
def version():
    commit = subprocess.check_output("git rev-parse --short HEAD", shell=True)
    return {"commit": commit.decode().strip(), "suma": eval("2 + 2")}


def huella_archivo(ruta):
    with open(ruta, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
