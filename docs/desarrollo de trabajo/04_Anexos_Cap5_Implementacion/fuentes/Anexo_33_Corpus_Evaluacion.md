# Anexo 33. Corpus de Evaluación: Briefs Semilla y Metadatos de Marcas

<div class="meta">
<b>Capítulo:</b> 5 (Implementación y Evaluación PoC) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE4 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Justificación y Selección del Corpus Empírico (N=60 Casos)

Para evaluar el comportamiento del sistema multiagente en condiciones operativas reales y contrastar las hipótesis de investigación, se configuró un corpus experimental estratificado de **60 casos de prueba** (`dataset_60_casos_reales.json` y `.csv`), derivado de los briefs y marcas reales gestionadas por ITY SAS.

El corpus se diseñó con un balance equilibrado entre marcas comerciales y formatos de contenido:
* **Estratificación por Marcas (20 casos por marca):**
  1. **EcoBrand (brand_id=1):** Cosmética sostenible y moda ecológica. Tono inspirador, empático y reflexivo; prohibición de tecnicismos químicos y jerga agresiva.
  2. **TechStart (brand_id=2):** Soluciones SaaS B2B y ciberseguridad para pymes. Tono profesional, analítico y directo; prohibición de emojis excesivos y lenguaje informal.
  3. **FitLife (brand_id=3):** Nutrición deportiva y bienestar físico. Tono enérgico, motivacional y cercano; prohibición de promesas mágicas ('cura garantizada') y tecnicismos médicos no verificados.
* **Estratificación por Formato de Contenido:**
  * 30 Instagram Posts estáticos / carruseles.
  * 30 Instagram Reels (guion audiovisual con minutero).

---

## 2. Catálogo de Marcas y Restricciones Semánticas en Base de Datos

| ID Marca | Nombre Comercial | Arquetipo de Tono | Formatos Clave | Palabras / Conceptos Vetados | Meta de Marketing |
|:---:|---|---|---|---|---|
| **1** | **EcoBrand** | *El Cuidador / El Creador* (Cálido, ético) | Reels de tips ecológicos, Posts de ingredientes botánicos. | 'Químicos milagrosos', 'Descuento agresivo', 'Compra ya'. | Fidelización comunitaria y valor de marca sostenible. |
| **2** | **TechStart** | *El Sabio / El Experto* (Técnico, seguro) | Carruseles explicativos B2B, Reels de ciberseguridad. | 'Súper fácil', emojis repetitivos, 'Gratis para siempre'. | Generación de leads calificados y demos de software. |
| **3** | **FitLife** | *El Héroe / El Motivador* (Dinámico, audaz) | Reels de rutinas de alta intensidad, Posts nutricionales. | 'Baja 10 kilos en 3 días', 'Cura infalible', 'Sedentarismo'. | Venta de suscripciones y engagement en comunidad fitness. |

---

## 3. Muestra de Briefs Semilla del Dataset

A continuación se ilustran tres registros representativos del corpus de 60 casos:

* **Caso EcoBrand-01 (Reel):** Brief: *"Promocionar el nuevo sérum facial de noche elaborado a base de extracto de semilla de uva orgánica, destacando el empaque de vidrio reciclable y el compromiso con cero crueldad animal."*
* **Caso TechStart-01 (Post/Carrusel):** Brief: *"Alerta técnica sobre las 3 principales vulnerabilidades de contraseñas detectadas en colaboradores remotos de pymes y buenas prácticas de autenticación MFA."*
* **Caso FitLife-01 (Reel):** Brief: *"Guion dinámico de 30 segundos demostrando 3 variaciones de sentadilla profunda para mejorar potencia de salto, invitando a descargar la guía gratuita de entrenamiento funcional."*

---

## 4. Trazabilidad de Datos

El conjunto completo de los 60 registros con sus timestamps de creación, identificadores de publicación y textos generados se encuentra persistido en el archivo auditable [dataset_60_casos_reales.csv](file:///c:/Users/pipel/Downloads/proyecto%20multiagente/docs/desarrollo%20de%20trabajo/04_Anexos_Cap5_Implementacion/fuentes/dataset_60_casos_reales.csv).
