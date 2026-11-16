const express = require("express");
const { exec } = require("child_process");

const app = express();

app.get("/buscar", (req, res) => {
  res.send("<h1>Resultados para " + req.query.q + "</h1>");
});

app.get("/historial", (req, res) => {
  exec("git log --oneline " + req.query.rama, (err, salida) => res.send(salida));
});

app.get("/estado", (req, res) => {
  exec("git status --short", (err, salida) => res.type("text").send(salida));
});

app.listen(3000);
