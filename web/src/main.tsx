import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

function App() {
  return (
    <main>
      <p className="eyebrow">Versión 2 · M0</p>
      <h1>Contratos listos para revisión</h1>
      <p>
        Esta estructura todavía no activa valoración, puntuación ni datos de proveedores.
        Es una frontera compilable para las siguientes entregas.
      </p>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
