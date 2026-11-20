# Dominio propio

El sitio se publica hoy en `https://arancel-mx.vercel.app`. Este documento es el procedimiento para pasar a un dominio propio sin dejar enlaces rotos: el cambio en el repositorio es **un comando** y el resto son pasos de cuenta (Vercel y el registrador del dominio).

## 1. En Vercel (antes de tocar el repositorio)

1. Proyecto `arancel-mx` → Settings → Domains → **Add** `www.tudominio.com` (y el apex `tudominio.com` si lo quieres; elige uno como principal).
2. Vercel muestra los registros DNS que faltan. En el registrador del dominio:
   - para un subdominio (`www`): un `CNAME` hacia el valor que indica Vercel;
   - para el apex: un `A` o el servidor de nombres de Vercel, según lo que Vercel indique.
3. Espera a que el dominio aparezca como *Valid Configuration* y a que Vercel emita el certificado.
4. Marca el dominio elegido como principal. Vercel redirige el otro (incluido `arancel-mx.vercel.app`) al principal con un 308, por lo que los enlaces compartidos hasta hoy siguen funcionando.

## 2. En el repositorio

```bash
node scripts/set-site-origin.mjs https://www.tudominio.com --dry-run   # lista lo que cambiaría
node scripts/set-site-origin.mjs https://www.tudominio.com             # lo cambia y reconstruye el frontend
```

El script reemplaza el origen actual (`SITE_ORIGIN` de `frontend/src/page-meta.js`) en todos los archivos de texto versionados salvo el changelog: etiquetas `canonical` y de compartir, `sitemap.xml`, `robots.txt`, el puente de la página, el canario `check_public_service.py`, los documentos y las pruebas que fijan la dirección. Después ejecuta `npm run build:frontend` para que el bundle con hash y el HTML por ruta coincidan. Revisa el diff, ejecuta las pruebas y abre un PR.

Las pruebas `tests/e2e/set-site-origin.test.mjs` fallan si un archivo del sitio nombra un origen distinto del configurado.

## 3. Después del despliegue

- En GitHub: Settings → About → *Website* con la dirección nueva, y la descripción del repositorio si la menciona.
- En el canario de producción (`scripts/check_public_service.py` o su workflow), confirmar que apunta al dominio nuevo (ya lo hace por el `DEFAULT_BASE_URL` que cambia el script).
- En Google Search Console y Bing Webmaster (si los usas): agregar el dominio nuevo y enviar `https://www.tudominio.com/sitemap.xml`.
- Probar una tarjeta de compartir (por ejemplo con el depurador de enlaces de cada red) con una ficha, p. ej. `/app/record/85171301`.

## Qué no cambia

- La API estática sigue en `/data/v1`, servida desde GitHub Pages a través de Vercel; no depende del dominio.
- Las URL de las releases en GitHub y los permalinks de la documentación no se tocan.

## Reversión

Ejecuta el mismo script con el origen anterior (`https://arancel-mx.vercel.app`) y quita el dominio en Vercel.
