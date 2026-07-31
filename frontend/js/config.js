/* Configuración del frontend. La API key debe coincidir con el backend
   (env INVERSOR_API_KEY). Puede sobrescribirse antes de este script con:
   <script>window.INVERSOR_API_KEY = "..."</script> */

export const API_KEY =
  (typeof window !== "undefined" && window.INVERSOR_API_KEY) ||
  "dev-secret-change-me";

export const CACHE_VERSION = "v26.0";
