# Propuesta de implementación
## Authority Resolution Layer para desambiguación de autores e instituciones

### Objetivo del documento
Presentar una propuesta técnica y de producto para construir e integrar una **Authority Resolution Layer (ARL)** en el proyecto de desambiguación de entidades, con foco inicial en **autores** y evolución posterior hacia **instituciones**. El objetivo es alinear al equipo de desarrollo y producto en alcance, arquitectura, modelo de datos, roadmap, riesgos, métricas y siguientes pasos de implementación.

---

## 1. Resumen ejecutivo

Se propone implementar una **capa de resolución de autoridades multifuente** que permita transformar nombres ambiguos provenientes de RIS, OpenAlex, WoS, Scopus u otras fuentes en **entidades resueltas, trazables y auditables**.

La solución combinará cuatro tipos de evidencia:

- **VIAF**: reconciliación bibliográfica y variantes nominales
- **ORCID**: identidad fuerte del investigador cuando exista
- **OpenAlex**: contexto académico, coautoría, afiliaciones y producción científica
- **Wikidata**: enlace semántico e interoperabilidad

La propuesta contempla una arquitectura híbrida con:

- **pipeline de normalización**
- **búsqueda federada de candidatos**
- **motor de scoring explicable**
- **persistencia de evidencia y decisiones**
- **revisión humana para casos ambiguos**

La implementación se plantea en fases, iniciando por **autores**, con un MVP técnicamente viable, medible y escalable hacia instituciones.

---

## 2. Problema que se busca resolver

### Situación actual
Las fuentes bibliográficas y académicas presentan variaciones de nombres, transliteraciones, errores de captura, cambios institucionales, iniciales, omisión de diacríticos y metadatos incompletos. Esto provoca:

- duplicación de entidades
- ambigüedad en autores con nombres similares
- pérdida de trazabilidad entre fuentes
- baja calidad en integración de datos
- dificultad para construir grafos y modelos enlazados confiables

### Impacto en producto
Sin una capa de resolución de autoridades:

- los perfiles de autor pueden fragmentarse
- las estadísticas y visualizaciones pueden ser incorrectas
- la búsqueda y exploración semántica pierden precisión
- las integraciones con grafos y Linked Open Data se vuelven frágiles

### Oportunidad
La ARL permitirá convertir metadatos heterogéneos en una base de entidades confiable, reutilizable y explicable, que sirva tanto para procesos operativos como para productos de exploración, descubrimiento y análisis.

---

## 3. Objetivos

### Objetivo general
Diseñar e implementar una capa de resolución de autoridades para desambiguar entidades bibliográficas de forma multifuente, explicable y escalable.

### Objetivos específicos
1. Resolver autores a partir de nombres ambiguos y metadatos contextuales.
2. Integrar identificadores externos confiables cuando existan.
3. Asignar niveles de confianza a cada resolución.
4. Preservar la evidencia usada para cada decisión.
5. Permitir revisión humana de casos ambiguos.
6. Preparar la arquitectura para extenderse a instituciones.

---

## 4. Alcance

### Fase inicial incluida
- Ingesta de registros desde RIS y fuentes API ya disponibles
- Extracción de autores y metadatos mínimos
- Normalización de nombres
- Generación de candidatos desde OpenAlex, VIAF, ORCID y Wikidata
- Scoring por evidencia
- Resolución automática con niveles de confianza
- Persistencia en base de datos relacional
- Exposición vía API interna
- Panel o interfaz básica para revisión manual

### Fuera del alcance inicial
- resolución plena de instituciones complejas
- corrección automática asistida por LLM en producción
- entrenamiento de modelos supervisados desde el día 1
- reconciliación masiva histórica de toda la base si no existe priorización

---

## 5. Principios de diseño

1. **Multifuente**: no depender de una sola autoridad.
2. **Explicable**: cada resolución debe conservar evidencia y score.
3. **Auditabilidad**: toda decisión debe poder revisarse.
4. **Escalabilidad**: arquitectura preparada para instituciones y otras entidades.
5. **Fallback seguro**: cuando no haya suficiente evidencia, no resolver automáticamente.
6. **Human in the loop**: los casos ambiguos deben escalar a revisión.
7. **Interoperabilidad**: IDs y salidas compatibles con RDF/graph y APIs.

---

## 6. Fuentes externas y rol dentro de la solución

### VIAF
Rol principal:
- clustering bibliográfico
- variantes de nombre
- reconciliación de autoridades bibliotecarias

Útil especialmente para:
- autores históricos
- nombres con múltiples variantes catalográficas
- integración con ecosistemas bibliotecarios

### ORCID
Rol principal:
- identidad persistente de autores contemporáneos
- validación fuerte cuando el ORCID está presente o es recuperable

Útil especialmente para:
- autores académicos vivos
- integración con producción científica

### OpenAlex
Rol principal:
- recuperación de autores candidatos
- contexto de afiliación, producción, coautoría y áreas temáticas

Útil especialmente para:
- matching contextual
- priorización de candidatos
- trazabilidad hacia works e institutions

### Wikidata
Rol principal:
- enriquecimiento semántico
- enlaces con otros identificadores
- contextualización transversal

Útil especialmente para:
- grafo abierto
- interoperabilidad semántica
- enriquecimiento posterior

---

## 7. Arquitectura propuesta

### Vista lógica

```text
Fuentes de entrada
(RIS / WoS / Scopus / OpenAlex / CSV / APIs)
        ↓
Parser de registros
        ↓
Extractor de entidades
        ↓
Normalizador de nombres
        ↓
Generador de variantes
        ↓
Buscador federado de candidatos
   ├─ OpenAlex
   ├─ VIAF
   ├─ ORCID
   └─ Wikidata
        ↓
Unificador de candidatos
        ↓
Motor de scoring
        ↓
Motor de decisión
   ├─ exact_match
   ├─ probable_match
   ├─ ambiguous
   └─ unresolved
        ↓
Persistencia + auditoría
        ↓
API interna + interfaz de revisión
        ↓
Graph / productos derivados
```

### Componentes técnicos
- **Ingestion Service**
- **Normalization Service**
- **Resolver Orchestrator**
- **Provider Connectors**
- **Scoring Engine**
- **Resolution Store**
- **Review Queue**
- **Admin/Reviewer UI**
- **Export Layer (API / RDF / GraphDB)**

---

## 8. Flujo funcional

1. entra un registro bibliográfico
2. se extraen autores y metadatos asociados
3. se normaliza el nombre
4. se generan variantes consultables
5. se consultan fuentes externas
6. se unifican candidatos
7. se calcula score por evidencia
8. se determina el estado de resolución
9. se guarda resultado y evidencia
10. si hay ambigüedad, pasa a revisión humana
11. la decisión final se publica para consumo interno y posterior exportación

---

## 9. Modelo de resolución

### Tipos de salida
- **exact_match**: alta confianza, resolución automática
- **probable_match**: confianza suficiente, con trazabilidad reforzada
- **ambiguous**: requiere revisión humana
- **unresolved**: no hay evidencia suficiente

### Enfoque de scoring
Se recomienda un modelo híbrido basado en reglas ponderadas.

#### Señales principales
**Identificadores fuertes**
- ORCID exacto
- OpenAlex ID ya vinculado
- VIAF ID previamente resuelto
- ISNI
- Wikidata QID asociado

**Señales nominales**
- coincidencia exacta del nombre normalizado
- coincidencia flexible sin diacríticos
- coincidencia por iniciales
- coincidencia de apellidos compuestos
- similitud de transliteración

**Señales contextuales**
- afiliación compatible
- coautoría recurrente
- área temática compatible
- idioma dominante
- país o región
- compatibilidad temporal

**Señales bibliográficas**
- DOI asociado
- coincidencia en títulos
- revista o venue repetido
- pertenencia a conjuntos documentales esperados

### Fórmula inicial sugerida
```text
score_total =
  0.35 * score_identificadores +
  0.25 * score_nombre +
  0.20 * score_afiliacion +
  0.10 * score_coautoria +
  0.10 * score_tematica
```

### Umbrales sugeridos
- `>= 0.85`: exact_match
- `0.65 - 0.84`: probable_match
- `0.45 - 0.64`: ambiguous
- `< 0.45`: unresolved

Estos umbrales deben calibrarse con un conjunto de evaluación real.

---

## 10. Reglas por tipo de entidad

### Autores
Estrategia inicial recomendada:
- alta prioridad a ORCID si existe
- OpenAlex como fuente principal de contexto
- VIAF para variantes y refuerzo bibliográfico
- Wikidata como capa semántica complementaria

### Instituciones
Debe tratarse como una segunda fase porque requiere:
- manejo de alias y siglas
- sedes y jerarquías internas
- fusiones y renombramientos
- temporalidad institucional
- distinción entre institución madre y subunidad

Conclusión: autores e instituciones no deben compartir exactamente las mismas reglas de matching.

---

## 11. Propuesta de arquitectura de implementación real

### Stack recomendado
- **Backend API**: FastAPI
- **Persistencia**: PostgreSQL
- **Tareas asíncronas**: Celery o Dramatiq con Redis
- **Cache de consultas externas**: Redis
- **Motor de búsqueda auxiliar**: PostgreSQL trigram / pgvector opcional
- **Serialización API**: Pydantic
- **Observabilidad**: Prometheus + Grafana o logs estructurados
- **Contenerización**: Docker
- **Despliegue**: según stack actual del proyecto

### Razón del stack
Encaja bien con una arquitectura modular, APIs internas limpias, pipelines de procesamiento y futura integración con GraphDB o capas RDF.

---

## 12. Diseño de módulos

### 12.1 Ingestion Module
Responsabilidades:
- recibir RIS/API payloads
- parsear registros
- extraer autores y metadatos mínimos
- generar identificadores internos

### 12.2 Normalization Module
Responsabilidades:
- normalizar Unicode
- limpiar puntuación
- estandarizar espacios
- separar nombre/apellidos
- generar variantes canónicas
- almacenar representación normalizada

### 12.3 Provider Connectors
Responsabilidades:
- encapsular integración con cada fuente externa
- manejar timeouts, retries y rate limiting
- devolver respuestas en formato interno común

Conectores iniciales:
- `openalex_connector`
- `viaf_connector`
- `orcid_connector`
- `wikidata_connector`

### 12.4 Candidate Unifier
Responsabilidades:
- transformar respuestas heterogéneas en candidatos comparables
- deduplicar candidatos entre fuentes
- enriquecer candidatos con señales normalizadas

### 12.5 Scoring Engine
Responsabilidades:
- calcular scores parciales
- explicar score total
- aplicar reglas por entidad y contexto

### 12.6 Resolution Engine
Responsabilidades:
- determinar estado final
- seleccionar candidato ganador si aplica
- emitir razones de decisión

### 12.7 Review Queue
Responsabilidades:
- almacenar casos ambiguos
- priorizar revisión
- registrar decisiones humanas
- retroalimentar calibración de umbrales

---

## 13. Modelo de datos sugerido

### Tabla: `raw_records`
```sql
id
source_name
source_record_id
title
year
doi
payload_json
created_at
```

### Tabla: `raw_authors`
```sql
id
raw_record_id
position
raw_name
raw_affiliation
raw_orcid
normalized_name
canonical_name
created_at
```

### Tabla: `external_candidates`
```sql
id
raw_author_id
provider
external_id
label
provider_payload_json
score_name
score_affiliation
score_context
score_identifiers
score_total
created_at
```

### Tabla: `author_resolutions`
```sql
id
raw_author_id
chosen_provider
chosen_external_id
resolution_status
confidence_score
resolution_reason
evidence_json
reviewed_by
review_status
created_at
updated_at
```

### Tabla: `entity_links`
```sql
id
local_entity_id
provider
external_id
link_type
created_at
```

### Tabla: `review_tasks`
```sql
id
entity_type
entity_local_id
priority
status
assigned_to
notes
created_at
updated_at
```

---

## 14. Contrato API interno sugerido

### POST `/ingest/record`
Recibe un registro bibliográfico o un lote pequeño.

### POST `/resolve/author/{raw_author_id}`
Dispara resolución para un autor concreto.

### POST `/resolve/batch`
Ejecuta resolución por lote.

### GET `/authors/{id}/candidates`
Devuelve candidatos y score.

### GET `/authors/{id}/resolution`
Devuelve resolución final, estado y evidencia.

### POST `/review/{resolution_id}/decision`
Permite registrar revisión humana.

### GET `/metrics/resolution`
Expone KPIs operativos y de calidad.

---

## 15. Ejemplo de respuesta JSON

```json
{
  "raw_author_id": "123",
  "normalized_name": "gabriel garcia marquez",
  "resolution_status": "probable_match",
  "chosen_candidate": {
    "provider": "viaf",
    "external_id": "95218065",
    "label": "García Márquez, Gabriel"
  },
  "confidence_score": 0.81,
  "score_breakdown": {
    "identifiers": 0.40,
    "name": 0.93,
    "affiliation": 0.20,
    "coauthorship": 0.55,
    "topic": 0.70
  },
  "evidence": [
    "name_exact_variant_match",
    "openalex_context_compatible",
    "viaf_cluster_contains_variant"
  ]
}
```

---

## 16. Roadmap de implementación

### Fase 0. Diseño y alineación
Duración estimada: 1 a 2 semanas

Entregables:
- modelo funcional aprobado
- definición de fuentes y prioridades
- dataset de prueba
- criterios de evaluación

### Fase 1. MVP autores
Duración estimada: 3 a 5 semanas

Entregables:
- parser de registros
- normalizador de nombres
- conectores OpenAlex y VIAF
- scoring inicial
- persistencia en Postgres
- endpoint de resolución

### Fase 2. Enriquecimiento y revisión
Duración estimada: 2 a 4 semanas

Entregables:
- integración ORCID y Wikidata
- review queue
- interfaz básica para casos ambiguos
- métricas operativas y panel inicial

### Fase 3. Calibración y hardening
Duración estimada: 2 a 3 semanas

Entregables:
- ajuste de umbrales
- mejoras de performance
- manejo de lotes
- retry, cache y observabilidad

### Fase 4. Instituciones
Duración estimada: posterior al cierre del MVP autores

Entregables:
- modelo de institución
- reglas específicas de matching institucional
- taxonomía de alias y jerarquías

---

## 17. KPIs recomendados

### Calidad de resolución
- porcentaje de autores resueltos automáticamente
- precisión de exact_match
- precisión de probable_match
- tasa de falsos positivos
- tasa de casos ambiguos
- cobertura por fuente

### Operación
- tiempo promedio de resolución
- latencia por proveedor
- tasa de errores por conector
- porcentaje de respuestas desde cache
- throughput por lote

### Producto
- reducción de duplicados visibles
- mejora en calidad de búsqueda
- aumento de perfiles consolidados
- mejora de navegación por autor

---

## 18. Riesgos y mitigaciones

### Riesgo 1: datos externos incompletos o inconsistentes
Mitigación:
- estrategia multifuente
- fallback a unresolved
- preservación de evidencia

### Riesgo 2: falsos positivos por exceso de automatización
Mitigación:
- umbrales conservadores
- revisión humana en zona gris
- auditoría completa

### Riesgo 3: dependencia excesiva de una sola fuente
Mitigación:
- conectores desacoplados
- modelo de candidato unificado
- pesos configurables

### Riesgo 4: performance en consultas masivas
Mitigación:
- cache
- colas de procesamiento
- límites por lote
- prefetch de candidatos frecuentes

### Riesgo 5: reglas insuficientes para instituciones
Mitigación:
- no mezclar complejidad institucional en MVP autores
- diseñar fase específica para instituciones

---

## 19. Recomendaciones de producto

1. Tratar la resolución como una **capacidad transversal** del sistema, no como una función aislada.
2. Incorporar desde el inicio una **explicación legible del porqué del match**.
3. Diseñar una vista de revisión humana simple pero útil:
   - nombre original
   - variantes
   - top candidatos
   - score y evidencias
   - decisión final
4. Definir una política explícita de **no resolución automática** cuando no haya certeza.
5. Medir éxito no solo por cobertura, sino por **precisión y reducción de errores visibles**.

---

## 20. Recomendaciones de desarrollo

1. Implementar conectores desacoplados por proveedor.
2. Mantener el scoring configurable por pesos y reglas.
3. Versionar el algoritmo de resolución.
4. Guardar payload original y payload transformado.
5. Separar claramente:
   - raw data
   - candidatos
   - resolución final
   - revisión humana
6. Diseñar pruebas con casos reales ambiguos desde el principio.
7. Preparar exportación futura a RDF o GraphDB sin forzarla en el MVP.

---

## 21. Siguiente arquitectura de trabajo propuesta

### Sprint 1
- definir dataset de evaluación
- cerrar modelo de datos
- construir parser de ingesta
- construir normalizador

### Sprint 2
- integrar OpenAlex
- integrar VIAF
- unificador de candidatos
- primer scoring funcional

### Sprint 3
- persistencia completa
- endpoint de resolución
- pruebas con casos reales
- métricas iniciales

### Sprint 4
- integrar ORCID/Wikidata
- cola de revisión
- pantalla básica de validación
- calibración inicial

---

## 22. Decisiones que el equipo debe cerrar

1. fuentes de entrada prioritarias del MVP
2. volumen esperado por lote
3. nivel de automatización aceptable
4. responsables de revisión humana
5. dataset de evaluación y criterio de verdad terreno
6. stack definitivo de observabilidad y despliegue
7. cuándo se exportará a grafo y en qué formato

---

## 23. Propuesta de decisión ejecutiva

Se recomienda aprobar un **MVP de Authority Resolution Layer enfocado exclusivamente en autores**, con arquitectura modular, scoring explicable y revisión humana, usando OpenAlex y VIAF como núcleo inicial, con ORCID y Wikidata en una segunda iteración corta.

Esta decisión reduce riesgo, permite validar impacto real rápidamente y deja una base sólida para escalar a instituciones y a un modelo de datos enlazados más amplio.

---

## 24. Cierre

La Authority Resolution Layer no debe verse solo como una integración técnica, sino como una **capacidad estratégica de calidad de datos, interoperabilidad y confianza del producto**. Su valor crece a medida que se integran más fuentes, más entidades y más casos de uso analíticos o semánticos.

Para el proyecto actual, la mejor ruta es:

- empezar por autores
- usar resolución multifuente
- conservar evidencia
- aceptar ambigüedad cuando corresponda
- construir desde el inicio una base auditable y reutilizable

Ese enfoque es el más realista para implementación inmediata y el más defendible para evolución futura.

---

## 25. Anexo: resumen en una frase

**OpenAlex encuentra, VIAF reconcilia, ORCID valida y Wikidata conecta; la ARL decide con evidencia, score y trazabilidad.**

