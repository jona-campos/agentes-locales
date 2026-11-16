const params = new URLSearchParams(window.location.search);
const nombre = params.get("nombre") || "visitante";
document.getElementById("saludo").innerHTML = "Hola, " + nombre;

const titulo = "Tienda";
document.getElementById("titulo").innerHTML = "<b>" + titulo + "</b>";

fetch("/clima").then((r) => r.json()).then((d) => {
  document.getElementById("clima").textContent = d.temperatura;
});
