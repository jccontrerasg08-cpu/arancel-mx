# Política de desarrollo verificable — Central Hub

**Versión de política:** 1.0

**Estado:** vigente al integrarse en `main`

**Fuente canónica:** este archivo en `jccontrerasg08-cpu/arancel-mx`

**Ámbito:** Central Hub (`arancel-mx`), backend RFA (`jccontrerasg08-cpu/auto-credito-2`) y frontend RFA (`PaginaWebRFA/PaginaWebRFA`).

## Propósito y alcance

Esta política convierte los principios de desarrollo del ecosistema en controles verificables. Protege la trazabilidad de datos, contratos públicos, secretos, personas usuarias y despliegues sin reemplazar el juicio técnico ni la revisión humana. Prevalece sobre convenciones implícitas, resúmenes históricos y atajos de entrega. Cada repositorio conserva su constitución técnica para reglas locales; cuando difieran, se aplica la regla más protectora y la discrepancia se resuelve mediante ADR.

> La seguridad no es una propiedad absoluta que pueda garantizarse. Esta política reduce riesgo evitable mediante mínimo privilegio, revisión, pruebas, evidencia y recuperación; no prueba que un sistema sea invulnerable.

| Área | Fuente de verdad operativa | Control mínimo compartido |
|---|---|---|
| Datos arancelarios públicos | Release certificado del Central Hub, sus fuentes oficiales y evidencia de procedencia | No mezclar versiones de datos, metadatos ni evidencia en una respuesta pública. |
| API, elegibilidad y documentos RFA | Backend FastAPI versionado | El navegador nunca decide autorización, ni conserva secretos, ni se vuelve fuente de verdad. |
| Experiencia RFA | Frontend React versionado | Consume contratos públicos versionados; trata todas las variables `VITE_*` como públicas. |
| Despliegue y paquetes | Commit, artefacto inmutable y entorno objetivo verificados por separado | Un build local no demuestra que producción use ese artefacto. |

## Principios obligatorios

Los siguientes principios se aplican a cualquier cambio de código, configuración, datos, documentación, dependencia, infraestructura o automatización. Un PR que no pueda demostrar los controles aplicables queda bloqueado o se marca explícitamente como excepción temporal.

| Principio | Regla operativa verificable |
|---|---|
| **Evidencia antes de cambio** | Se inspecciona el artefacto, configuración o fuente primaria antes de afirmar un problema o aplicar una corrección. Cada hecho importante se clasifica como confirmado, inferido, no verificado o bloqueado. |
| **Cambio mínimo y reversible** | Se reutiliza el control existente antes de crear uno nuevo. Todo cambio material identifica alcance, rollback y criterio de verificación antes de integrarse. |
| **Contrato primero** | Ningún contrato HTTP, paquete, dataset, CLI, esquema o variable pública cambia de forma incompatible sin versión, consumidor identificado, pruebas y plan de transición. |
| **Fuente única por tipo de dato** | Un dato operativo tiene un dueño y versión activa. Proyecciones, cachés y bundles deben declarar de qué release proceden y rechazar mezclas de versión. |
| **Seguridad y privacidad por defecto** | Secretos, PII, CFDI/XML reales, documentos, capturas, bases, llaves y URLs firmadas no entran en Git, artefactos públicos, fixtures ni logs. |
| **Mínimo privilegio** | Usuarios, tokens, runners, contenedores, buckets y servicios reciben sólo los permisos, orígenes y retención indispensables para su función. |
| **Deuda explícita** | TODO, fallback, excepción, compatibilidad temporal, archivo histórico o supresión de seguridad incluye propietario, razón, fecha de revisión y condición de salida. |
| **Afirmaciones calibradas** | No se declara "seguro", "desplegado", "actualizado" o "completo" sin una observación proporcional. Los límites de una comprobación se publican junto con su resultado. |

## Jerarquía documental y de archivos

La documentación vigente describe cómo funciona y se mantiene el sistema; la histórica sólo aporta contexto. Esta clasificación evita que un resumen retirado dirija una decisión de producción.

| Ubicación | Uso permitido | No permitido |
|---|---|---|
| `README.md` | Entrada de contribución, contrato de instalación y ruta a normas vigentes | Sustituir ADRs, runbooks o evidencia detallada. |
| `docs/architecture/` | Constitución, límites, propiedad de datos y dependencias vigentes | Planes descartados o notas de sesión. |
| `docs/decisions/` | ADRs con contexto, decisión, consecuencias y revisión | Ocultar excepciones sin fecha de expiración. |
| `docs/governance/` | Políticas, controles, matrices de riesgo y procesos de revisión | Evidencia efímera no fechada. |
| `docs/runbooks/` | Operación reproducible, recuperación y verificación post-despliegue | Credenciales, secretos o datos reales. |
| `docs/verification/` | Resultado fechado de comandos, pruebas, fuentes y límites | Afirmaciones sin método, fecha o alcance. |
| `docs/history/` | Material retirado y preservado con índice y motivo | Definir el comportamiento actual. |

No se elimina un archivo por antigüedad, tamaño o apariencia. Primero se registra su clasificación, se comprueba que no tiene referencias de runtime, workflows, pruebas, README ni documentación vigente, y se solicita confirmación humana antes de borrar. Si no hay autorización de borrado, se conserva y se archiva con enlaces internos actualizados.

## Puerta de cambio basada en evidencia

Cada PR declara de forma legible el dominio afectado, riesgo, datos, contratos, verificación, rollback y limitaciones. Los controles se seleccionan por impacto, no por comodidad.

| Tipo de cambio | Evidencia mínima antes de integración | Evidencia adicional requerida |
|---|---|---|
| Código o configuración interna | Compilación, prueba dirigida, revisión de diferencia y control de higiene | Suite relevante y análisis estático cuando cambia superficie de seguridad. |
| Contrato público, paquete o frontend | Pruebas de contrato/consumidor y build del artefacto | Comprobación del artefacto publicado o del entorno real cuando se despliega. |
| Datos regulatorios o de negocio | Fuente primaria, versión, conteos/invariantes y muestra representativa | Comparación contra la release anterior y verificación del servicio que los expone. |
| Auth, autorización, PII, documentos, secretos o pagos | Prueba negativa/hostil, revisión de acceso y logs | Dos revisiones humanas cuando la plataforma lo permita; rollback probado o documentado. |
| Dependencia, imagen o infraestructura | Fuente/versiones fijadas, auditoría y prueba de runtime o build | Evaluación de compatibilidad, exposición y ruta de reversión. |
| Producción | Commit y artefacto identificados, resultado de despliegue y smoke test | Verificación separada de datos, rutas críticas y observabilidad. |

La evidencia adjunta al PR corresponde al commit exacto propuesto. Si CI no puede ejecutarse, la falla —incluido el estado sin runner— se conserva como evidencia bloqueada. Una verificación local puede ser una puerta manual compensatoria sólo si el responsable registra comando, salida, entorno, commit y alcance; nunca se convierte en éxito automático de CI.

## Seguridad, secretos y dependencias

Los repositorios mantienen detectores de secretos, verificadores de higiene, revisión de dependencias, análisis estático y pruebas. Estos controles no autorizan suprimir hallazgos sin una justificación específica y acotada.

| Control | Regla de cumplimiento |
|---|---|
| Secretos y datos sensibles | Se usan gestores de secretos y variables de entorno protegidas. `.env`, llaves, certificados, datos de operación y artefactos generados permanecen fuera del historial y del contexto de construcción de imágenes. |
| Dependencias | Se fijan o acotan de forma reproducible; se revisan alertas de seguridad y cambios de licencia. Una actualización insegura o incompatible no se integra sólo por automatización. |
| SQL y entradas | Los valores se enlazan como parámetros. Los identificadores dinámicos requieren allowlist cerrada y prueba de regresión. Una supresión estática requiere explicación, alcance y fecha de revisión. |
| Navegador | No se incluyen secretos en el bundle. CSP, CORS, orígenes de media, CAPTCHA, almacenamiento local y analítica se revisan como superficie de datos. |
| Contenedores | Se excluyen secretos y estado local del contexto de build; el proceso de aplicación se ejecuta sin privilegios innecesarios y los permisos de runtime son restrictivos. |
| Acceso y despliegue | `main` usa protección exigible cuando la plataforma lo permite. Si el plan no lo admite, se aplica una puerta manual: PR, dos revisiones para alto impacto cuando sea posible, evidencia del commit exacto y registro de excepción. |

Las variables que por diseño son públicas —por ejemplo, `VITE_*`— no se tratan como secretos. Toda nueva variable pública se agrega a una allowlist, se documenta su propósito y se revisa su exposición antes del build.

## Cambios entre repositorios

Un cambio que atraviesa Central Hub, backend o frontend mantiene una matriz de compatibilidad en el PR o ADR. La matriz identifica productor, consumidor, versión, ventana de transición, prueba de contrato y responsable. La coexistencia de versiones se retira sólo después de observar consumidores actualizados o de que expire la ventana documentada.

| Productor | Consumidor | Regla |
|---|---|---|
| Dataset certificado del Central Hub | API, web, paquete Python, proyección de base | Todos declaran la misma identidad de release o la respuesta se rechaza. |
| Backend RFA | Frontend RFA | La API publica un contrato versionado; una SPA no deriva reglas de autorización ni de elegibilidad. |
| Repositorio | Entorno de producción | El commit no se da por desplegado hasta observar el artefacto/ruta activa en el proveedor correspondiente. |

## Excepciones, revisión y recuperación

Una excepción requiere ADR o registro de gobernanza con: regla afectada, razón, análisis de riesgo, propietario, controles compensatorios, fecha de expiración, plan de retiro y evidencia de revisión. Las excepciones caducadas bloquean cambios relacionados hasta renovarse o retirarse.

Todo cambio de datos, despliegue, secreto, almacenamiento, media o migración documenta cómo volver al estado previo. No se mezclan en una sola PR la migración irreversible y la eliminación de su ruta de recuperación. Después de un incidente, se conserva una revisión sin secretos ni datos personales, con causa, impacto, corrección, verificación y acciones de prevención.

## Revisión de esta política

La persona responsable del repositorio revisa esta política al menos trimestralmente y después de un incidente relevante, cambio de proveedor, cambio regulatorio, modificación de límites de plataforma o hallazgo de auditoría. Los cambios se proponen mediante PR, con evidencia de compatibilidad y, si modifican obligaciones, un ADR.

Las constituciones de `auto-credito-2` y `PaginaWebRFA` adoptan esta política como línea común y detallan los controles específicos de backend y frontend. Un repositorio no puede debilitar esta política localmente; sólo puede añadir controles más estrictos.
