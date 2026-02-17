# Arquitectura y Patrones de Ingeniería de Software

## DB Disambiguator — Documentación Técnica de Diseño

**Última actualización:** 2026-02-17  
**Versión del documento:** 2.0

---

## Índice

1. [Filosofía de Diseño](#1-filosofía-de-diseño)
2. [Visión General](#2-visión-general)
3. [Principios SOA Aplicados con Pragmatismo](#3-principios-soa-aplicados-con-pragmatismo)
4. [Modelo de Madurez Evolutiva](#4-modelo-de-madurez-evolutiva)
5. [Arquitectura General](#5-arquitectura-general)
6. [Patrones de Diseño](#6-patrones-de-diseño)
7. [Patrones Estructurales](#7-patrones-estructurales)
8. [Patrones de Integración](#8-patrones-de-integración)
9. [Patrones de Frontend](#9-patrones-de-frontend)
10. [Patrones de Datos](#10-patrones-de-datos)
11. [Decisiones Técnicas Clave](#11-decisiones-técnicas-clave)
12. [Diagrama de Flujo de Datos](#12-diagrama-de-flujo-de-datos)
13. [Anti-Patrones: Lo Que Decidimos NO Hacer](#13-anti-patrones-lo-que-decidimos-no-hacer)
14. [Guía de Decisión para Nuevas Features](#14-guía-de-decisión-para-nuevas-features)

---

## 1. Filosofía de Diseño

### El Principio Rector: Complejidad Justificada

> *"La perfección no se alcanza cuando no hay nada más que agregar, sino cuando no hay nada más que quitar."*  
> — Antoine de Saint-Exupéry

Este proyecto se rige por una regla fundamental: **cada patrón, cada capa de abstracción y cada decisión arquitectónica debe justificar su existencia resolviendo un problema real y concreto**. No adoptamos patrones porque "es lo que se debe hacer" en la industria, sino porque resuelven un dolor específico que tenemos *hoy* o que tenemos *certeza razonable* de que tendremos mañana.

### 1.1 — La Curva de la Sobre-Ingeniería

```
Productividad
     ▲
     │            ╱╲
     │           ╱  ╲        ← Zona de Sobre-Ingeniería
     │          ╱    ╲         (más capas, más abstracto,
     │    ●────╱      ╲        pero más lento y frágil)
     │   ╱              ╲
     │  ╱                ╲
     │ ╱                  ╲
     │╱                    ╲
     ├──────────────────────────────► Complejidad Arquitectónica
     │
     Sub-ingeniería  │  Punto   │  Sobre-ingeniería
     (código espagueti)│ Óptimo  │  (astronaut architecture)
```

La sobre-ingeniería es tan dañina como la sub-ingeniería, pero es más insidiosa porque *se siente* productiva. Escribir una interfaz abstracta, tres capas de herencia y un patrón Strategy para algo que podría ser un `if/else` tiene un costo real:

- **Costo cognitivo**: Cada capa de indirección es una capa más que un desarrollador debe comprender.
- **Costo de mantenimiento**: Más archivos, más clases, más tests, más superficie de bugs.
- **Costo de velocidad**: Las abstracciones prematuras congelan decisiones que todavía no entendemos bien.

### 1.2 — Los Tres Filtros de Decisión

Antes de introducir cualquier patrón o abstracción, debe pasar estos tres filtros:

```
┌──────────────────────────────────────────────────────────────┐
│  FILTRO 1: ¿Resuelve un problema que TENEMOS HOY?            │
│  ─────────────────────────────────────────────────            │
│  Si la respuesta es SÍ → Implementar la solución más         │
│  simple que resuelva el problema completo.                    │
│                                                              │
│  Si la respuesta es NO → Pasar al Filtro 2.                  │
├──────────────────────────────────────────────────────────────┤
│  FILTRO 2: ¿El costo de NO implementarlo ahora es alto?      │
│  ─────────────────────────────────────────────────            │
│  ¿Tendría que reescribir código significativo después?        │
│  ¿Violaría un contrato público (API, esquema de BD)?         │
│                                                              │
│  Si SÍ → Implementar la infraestructura mínima.              │
│  Si NO → Pasar al Filtro 3.                                  │
├──────────────────────────────────────────────────────────────┤
│  FILTRO 3: ¿Es gratis o casi gratis?                         │
│  ─────────────────────────────────────                        │
│  ¿Se puede hacer sin agregar complejidad visible?            │
│                                                              │
│  Si SÍ → Hacerlo (ej. nombrar bien una variable).            │
│  Si NO → NO HACERLO. Documentar como decisión futura.        │
└──────────────────────────────────────────────────────────────┘
```

### 1.3 — Ejemplos Concretos de los Filtros en Acción

| Decisión | Filtro | Resultado |
|----------|--------|-----------|
| Usar ORM (SQLAlchemy) en lugar de SQL crudo | Filtro 1 ✅ | Resuelve un problema hoy: 60+ columnas, queries repetitivas, portabilidad de BD. |
| Patrón Adapter para tiendas | Filtro 1 ✅ | Resuelve un problema hoy: 4 APIs distintas con autenticación y formatos diferentes. |
| Usar `BaseStoreAdapter` como ABC | Filtro 2 ✅ | Si no definimos la interfaz ahora, cada adaptador tendría métodos diferentes y el motor de sync no podría ser genérico. |
| NO implementar microservicios | Filtro 1 ❌ | Un solo proceso maneja la carga actual. No hay problema de escala que resolver. |
| NO usar Event Sourcing | Filtro 1 ❌ | El `SyncLog` + `SyncQueueItem` resuelven la auditoría sin la complejidad de reconstruir estado desde eventos. |
| NO usar cache (Redis) | Filtro 1 ❌ | Las queries actuales contra SQLite son sub-milisegundo. No hay problema de rendimiento. |
| Usar diccionario simple para i18n | Filtro 3 ✅ | Con 2 idiomas y ~30 claves, un diccionario TypeScript es literalmente gratis. No agrega complejidad. |
| NO crear un Service Layer separado | Filtro 2 ❌ | La lógica de negocio vive en los endpoints y no se duplica aún. Extraer servicios hoy sería mover código sin ganancia. |

### 1.4 — La Regla de las Tres Repeticiones

> **No abstraigas hasta que lo necesites tres veces.**

```
Primera vez:  Escribe la solución directa.
Segunda vez:  Nota la similitud, pero tolera la duplicación.
Tercera vez:  AHORA abstractiza. Ya entiendes el patrón real.
```

Esto aplica a todo: funciones utilitarias, componentes React, endpoints de API. La razón: **la primera y segunda vez no tienes suficiente información para saber qué parte es la que realmente se repite**. Abstraer prematuramente frecuentemente captura las accidentalidades (lo que coincide por casualidad) en lugar de las esencialidades (lo que realmente es un patrón).

**Ejemplo real del proyecto:**
- Cuando solo teníamos WooCommerce, NO creamos `BaseStoreAdapter`. Lo habríamos diseñado alrededor de las particularidades de WooCommerce.
- Cuando agregamos Shopify (segundo caso), vimos similitudes pero aún no estaba claro el contrato mínimo.
- Al planificar Bsale y Custom (tercero y cuarto), *ya entendemos exactamente qué necesitan todos*: `test_connection()`, `fetch_products()`, `push_product_update()`. La abstracción es precisa porque está basada en experiencia, no en especulación.

---

## 2. Visión General

DB Disambiguator es una herramienta de gestión de catálogo de productos que permite desambiguar, normalizar, armonizar y sincronizar datos de productos provenientes de distintas fuentes (archivos Excel, APIs de tiendas virtuales).

La aplicación está diseñada como un **monorepo** con dos módulos claramente separados:

```
DBDesambiguador/
├── backend/          ← API REST (Python / FastAPI)
│   ├── adapters/     ← Patrón Adapter para tiendas
│   ├── main.py       ← Endpoints centralizados
│   ├── models.py     ← Modelos SQLAlchemy (ORM)
│   ├── schemas.py    ← Validación de datos (Pydantic)
│   └── database.py   ← Configuración de BD
├── frontend/         ← SPA (Next.js / React / TypeScript)
│   ├── app/          ← App Router (file-based routing)
│   ├── components/   ← Componentes reutilizables
│   ├── contexts/     ← Estado global (React Context)
│   └── i18n/         ← Internacionalización
├── data/             ← Archivos de entrada (Excel)
├── docs/             ← Documentación
└── scripts/          ← Utilidades de CLI
```

---

## 3. Principios SOA Aplicados con Pragmatismo

### ¿Qué nos llevamos de SOA y qué dejamos?

SOA (Service Oriented Architecture) propone principios valiosos. Sin embargo, la implementación clásica de SOA (ESB, WSDL, orquestadores centrales) es un ejemplo perfecto de sobre-ingeniería cuando se aplica a proyectos que no la necesitan. Lo que hacemos es **extraer los principios y aplicarlos al nivel de complejidad que corresponde**.

### 3.1 — Loose Coupling (Débil Acoplamiento) ✅ Adoptado

> *"Los componentes deben saber lo mínimo necesario sobre los demás."*

**En SOA clásico:** Servicios independientes comunicándose vía message bus.  
**En nuestro proyecto:** Módulos Python y componentes React que se comunican vía contratos bien definidos.

```
                    Acoplamiento en nuestro sistema
                    
  Frontend ──── HTTP/JSON ────► Backend ──── ORM ────► BD
       │                            │
       │    No sabe que existe      │    No sabe que existe
       │    Python ni SQLite        │    React ni Next.js
       │                            │
       │    Solo conoce:            │    Solo conoce:
       │    • URLs de endpoints     │    • Modelos SQLAlchemy
       │    • Shapes de JSON        │    • Schemas Pydantic
       ▼                            ▼

  Adapters ──── HTTP ────► APIs Externas
       │
       │    El motor de sync
       │    no sabe qué plataforma
       │    es. Solo ve
       │    BaseStoreAdapter.
       ▼
```

**Dónde lo aplicamos y por qué:**

| Componente | Está acoplado a... | NO está acoplado a... | Beneficio real |
|------------|--------------------|-----------------------|----------------|
| Frontend | Formato JSON de respuestas | Python, SQLAlchemy, lógica de negocio | Se puede reescribir sin tocar backend |
| Endpoints | Schemas Pydantic, ORM | Frontend, estructura de BD física | Cambiar columnas de BD no rompe la API |
| Adapters | `BaseStoreAdapter` interface | Motor de sync, otros adapters | Agregar plataforma no afecta nada más |
| Motor de sync | `RemoteProduct` normalizado | APIs externas, autenticación específica | La lógica de sync es idéntica para toda plataforma |

**Dónde NO lo aplicamos (y por qué):**

No separamos `main.py` en múltiples microservicios porque:
- Un solo proceso sirve todas las rutas. No hay contención de recursos.
- La comunicación interna (función → función) es órdenes de magnitud más rápida que HTTP internos.
- Debugging de un proceso monolítico es trivial comparado con debugging distribuido.

### 3.2 — Service Contracts (Contratos de Servicio) ✅ Adoptado

> *"El contrato entre consumidor y proveedor debe ser explícito, estable y versionable."*

**En SOA clásico:** WSDL, XML Schema, contratos formales.  
**En nuestro proyecto:** Pydantic schemas + OpenAPI auto-generado.

```python
# Este schema ES el contrato. Pydantic lo valida, FastAPI lo documenta.
class StoreConnectionCreate(BaseModel):
    name: str                         # Obligatorio
    platform: str                     # Obligatorio
    base_url: str                     # Obligatorio
    api_key: Optional[str] = None     # Opcional
    sync_direction: str = "bidirectional"  # Default

class StoreConnectionResponse(BaseModel):
    id: int
    name: str
    platform: str
    is_active: bool
    # api_key: EXCLUIDO del contrato de salida ← Decisión de seguridad
```

**¿Por qué no WSDL o GraphQL Schema?**

- WSDL es para ecosistemas SOAP/enterprise. Nosotros usamos REST/JSON.
- GraphQL resuelve el problema de over-fetching/under-fetching que NO tenemos (nuestros endpoints retornan exactamente lo necesario).
- Pydantic schemas hacen lo mismo con menos ceremonia: validación, documentación y tipado automático.

### 3.3 — Service Reusability (Reusabilidad de Servicios) ✅ Adoptado selectivamente

> *"Un servicio debe ser diseñado para ser reutilizable más allá de su caso de uso original."*

**Lo que SÍ hacemos reutilizable:**
- Los adapters: `WooCommerceAdapter` puede usarse en cualquier contexto que necesite comunicarse con WooCommerce.
- Los schemas: Cualquier cliente (no solo nuestro frontend) puede consumir la API porque está documentada vía OpenAPI.
- Las funciones de utilidad: Mapeo de columnas, normalización de texto.

**Lo que NO hacemos reutilizable (intencionalmente):**
- Las páginas del frontend. Son específicas de esta aplicación. Hacerlas "reutilizables" sería abstraer sin beneficiario.
- Los endpoints. Están diseñados para los casos de uso de esta app. No pretendemos ser una "plataforma" genérica.

### 3.4 — Abstraction (Abstracción) ✅ Adoptado con mesura

> *"Un servicio debe ocultar su implementación interna."*

```
  ┌──────────────────────────────────────────────────────┐
  │         Lo que ve el consumidor (Frontend)            │
  │                                                      │
  │   POST /stores/1/pull  →  { new_mappings: 5 }       │
  │                                                      │
  ├──────────────────────────────────────────────────────┤
  │         Lo que pasa internamente (oculto)             │
  │                                                      │
  │   1. Buscar store en BD                              │
  │   2. Instanciar WooCommerceAdapter vía factory       │
  │   3. Llamar API con Basic Auth                       │
  │   4. Parsear JSON de WooCommerce                     │
  │   5. Normalizar a RemoteProduct                      │
  │   6. Comparar contra mapeos existentes               │
  │   7. Detectar cambios campo por campo                │
  │   8. Crear SyncQueueItems                            │
  │   9. Registrar en SyncLog                            │
  │  10. Commit a BD                                     │
  │                                                      │
  └──────────────────────────────────────────────────────┘
```

**El nivel correcto de abstracción:**
- El frontend NO sabe que internamente usamos un patrón Adapter. Solo sabe que `POST /stores/1/pull` retorna resultados.
- Los endpoints NO saben qué API específica están llamando. Solo saben que `adapter.fetch_products()` retorna `RemoteProduct[]`.
- Los adapters NO saben qué hará el motor de sync con los datos.

Cada capa sabe exactamente lo que necesita y **nada más**.

### 3.5 — Composability (Composabilidad) ✅ Adoptado

> *"Los servicios pueden combinarse para crear funcionalidad mayor."*

```
  Pull completo = Adapter.fetch_products()
                + Canonical URL Matching
                + Change Detection
                + Queue Creation
                + Sync Logging

  Cada pieza es independiente y testeable por separado.
```

### 3.6 — Statelessness (Sin estado) ⚠️ Adoptado parcialmente

> *"Los servicios no deben mantener estado entre llamadas."*

- **API REST**: Completamente sin estado. Cada request lleva toda la información necesaria. No hay sesiones en el servidor.
- **Adapters**: Sin estado. Se instancian por request y se descartan.
- **Frontend**: Tiene estado local (React state, Context). Esto es deliberado —el estado de UI es inherentemente del cliente.

**¿Por qué no 100% stateless?** Porque ser purista con statelessness en el frontend llevaría a re-fetch constantes, degradando la experiencia. El pragmatismo gana.

### 3.7 — Autonomy y Discoverability ❌ No adoptados (aún)

> *"Cada servicio es autónomo y auto-descriptivo."*

- **Autonomy**: No tenemos servicios independientes. Tenemos un monolito bien estructurado. La autonomía se vuelve relevante cuando tengamos múltiples equipos o necesitemos despliegue independiente.
- **Discoverability**: El Swagger auto-generado (`/docs`) cubre la descubrilidad por ahora. Un service registry (Consul, Eureka) sería sobre-ingeniería pura en nuestra escala.

---

## 4. Modelo de Madurez Evolutiva

### La arquitectura no es estática — evoluciona con el proyecto

En lugar de diseñar para el "caso máximo" desde el día uno, definimos **puntos de inflexión** claros donde la complejidad se justifica:

```
    Fase 1 (actual)          Fase 2                    Fase 3
    ─────────────           ─────────────              ─────────────
    Monolito simple    →    Monolito modular      →    Servicios separados
    SQLite             →    PostgreSQL            →    PostgreSQL + Redis
    1 archivo main.py  →    main.py + services/   →    API Gateway + servicios
    fetch() directo    →    Client SDK/hooks      →    GraphQL o gRPC
    Dict i18n          →    react-i18next         →    CMS headless
    Context API        →    Zustand/TanStack      →    Estado distribuido
```

### 4.1 — Triggers de Evolución (cuándo escalar)

Cada evolución tiene un **trigger concreto y medible**. No escalamos "por si acaso":

| Trigger | Señal concreta | Acción |
|---------|----------------|--------|
| `main.py` supera 2000 líneas | Dificultad para navegar, merge conflicts frecuentes | Extraer a `services/sync.py`, `services/products.py`, `services/harmonization.py` |
| Más de 5 requests simultáneos causan lentitud | Tiempos de respuesta > 500ms en queries de BD | Migrar de SQLite a PostgreSQL con connection pooling |
| Más de 3 idiomas o 100+ claves i18n | El diccionario plano se vuelve difícil de mantener | Adoptar `react-i18next` o `next-intl` |
| Múltiples equipos trabajan en el proyecto | Merge conflicts diarios en archivos compartidos | Considerar separar frontend y backend en sub-repos |
| El frontend necesita datos de múltiples endpoints para una vista | Over-fetching o waterfalls de requests | Evaluar GraphQL o endpoint de agregación |
| Necesidad de procesamiento en background (syncs largos) | Timeouts en pulls de > 500 productos | Incorporar Celery o un task queue |
| Múltiples usuarios concurrentes (> 10) | Conflictos de escritura en SQLite | PostgreSQL + row-level locking |
| Necesidad de cache por latencia de APIs externas | Pulls repetidos a la misma tienda en minutos | Redis como cache de respuestas de adapters |

### 4.2 — El Principio del Costo Diferido

```
  Costo de implementar HOY                  Costo de implementar DESPUÉS
  sin necesidad real:                        cuando se necesite:
  
  ┌─────────────────────┐                   ┌─────────────────────┐
  │ • Diseño especulativo│                   │ • Diseño informado  │
  │ • Código muerto      │                   │ • Solo lo necesario │
  │ • Tests de código    │                   │ • Tests relevantes  │
  │   que no se usa      │                   │ • Refactor focalizado│
  │ • Mantenimiento de   │                   │                     │
  │   abstracciones      │                   │ Costo total: MENOR  │
  │   innecesarias       │                   └─────────────────────┘
  │                      │
  │ Costo total: MAYOR   │
  └─────────────────────┘
```

**La excepción clave:** Si diferir una decisión implica romper un contrato público (schema de BD, API endpoint, formato de exportación), entonces SÍ vale la pena invertir ahora en diseñar la interfaz correcta, incluso si la implementación es simple.

### 4.3 — Mapa de lo que YA implementamos vs. lo que DIFERIMOS

| Categoría | Implementado (justificado) | Diferido (no necesario aún) |
|-----------|----------------------------|-----------------------------|
| **Arquitectura** | Cliente-Servidor separado | Microservicios, API Gateway |
| **Datos** | ORM con SQLAlchemy | Migraciones Alembic, PostgreSQL |
| **Integración** | Adapter Pattern + Factory | Message Queue, Event Bus |
| **Sync** | Cola de revisión humana | Sync automático, Webhooks |
| **Seguridad** | Credenciales excluidas de responses | OAuth2, JWT, RBAC |
| **Frontend** | React Context, file routing | State management library, GraphQL |
| **i18n** | Diccionario TypeScript | Librería i18n completa |
| **Testing** | Validación manual + curl | Unit tests, integration tests, CI/CD |
| **Deploy** | Dev servers locales | Docker Compose, Kubernetes |
| **Observabilidad** | SyncLog en BD | Prometheus, Grafana, ELK Stack |

---

## 5. Arquitectura General

### 5.1 — Client-Server Architecture (Arquitectura Cliente-Servidor)

```
┌──────────────────┐         HTTP/JSON         ┌──────────────────┐
│                  │  ◄──────────────────────►  │                  │
│   Frontend       │                            │   Backend        │
│   (Next.js)      │    GET, POST, PUT, DELETE  │   (FastAPI)      │
│   Puerto: 3004   │                            │   Puerto: 8000   │
│                  │                            │                  │
└──────────────────┘                            └────────┬─────────┘
                                                         │
                                                         ▼
                                                ┌──────────────────┐
                                                │   SQLite DB      │
                                                │   (sql_app.db)   │
                                                └──────────────────┘
```

**¿Por qué y no un monolito full-stack (como Django templates)?**

- **Separación de responsabilidades**: El frontend se encarga exclusivamente de la presentación y la interacción del usuario. El backend maneja la lógica de negocio, validación y persistencia. Esto permite que ambos evolucionen independientemente.
- **Flexibilidad de despliegue**: Se pueden escalar, desplegar o reemplazar de forma independiente. El backend podría ser consumido por otros clientes (apps móviles, scripts CLI) sin cambios.
- **Contratos claros**: La comunicación se realiza exclusivamente vía API REST con JSON, creando un contrato bien definido entre las capas.
- **¿No es esto sobre-ingeniería?** No, porque la separación es esencialmente "gratis" con FastAPI + Next.js, y resuelve un problema real: poder iterar en la UI sin riesgo de romper la lógica de datos.

---

## 6. Patrones de Diseño

### 6.1 — Repository Pattern (implícito vía SQLAlchemy ORM)

**Archivo:** `backend/models.py`, `backend/database.py`

```python
# database.py — Sesión centralizada
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# En endpoints:
def get_products(db: Session = Depends(get_db)):
    return db.query(models.RawProduct).all()
```

**¿Por qué?**

- **Abstracción del almacenamiento**: Los endpoints no necesitan saber si los datos vienen de SQLite, PostgreSQL o cualquier otro motor. Solo interactúan con objetos Python.
- **Gestión automática del ciclo de vida**: El patrón `yield` con `Depends()` asegura que cada request obtiene su propia sesión de BD, y que se cierra correctamente al finalizar — evitando fugas de conexiones.
- **Portabilidad**: Cambiar de SQLite a PostgreSQL requiere solo modificar `SQLALCHEMY_DATABASE_URL`. Los modelos y queries no cambian.

**¿Por qué NO un Repository explícito (clase `ProductRepository`)?**

Porque el `Session` de SQLAlchemy YA es un repository. Crear una clase wrapper solo agregaría una capa de indirección sin funcionalidad nueva. Cuando tengamos queries complejas que se repitan en múltiples endpoints (trigger: 3 repeticiones), extraeremos funciones de consulta — no antes.

---

### 6.2 — Data Transfer Object (DTO) / Schema Validation con Pydantic

**Archivo:** `backend/schemas.py`

```python
class StoreConnectionCreate(BaseModel):
    name: str
    platform: str
    base_url: str
    api_key: Optional[str] = None
    # ...

class StoreConnectionResponse(BaseModel):
    id: int
    name: str
    platform: str
    is_active: bool
    # Credenciales EXCLUIDAS intencionalmente
    class Config:
        from_attributes = True
```

**¿Por qué?**

- **Validación automática**: FastAPI valida cada request contra el schema antes de ejecutar la lógica. Un campo faltante o de tipo incorrecto se rechaza con un error 422 antes de llegar al código.
- **Seguridad por diseño**: Los schemas de respuesta (`StoreConnectionResponse`) excluyen deliberadamente campos sensibles como `api_key` y `api_secret`. Esto hace imposible que credenciales se filtren accidentalmente al frontend.
- **Documentación viva**: Los schemas generan automáticamente la documentación OpenAPI (Swagger) en `/docs`, creando un contrato API siempre actualizado.
- **Separación de concerns**: Un modelo ORM (`models.StoreConnection`) difiere del input esperado (`StoreConnectionCreate`) y de la respuesta enviada (`StoreConnectionResponse`). Esto permite que la BD tenga campos que nunca se exponen.

---

### 6.3 — Adapter Pattern (Patrón Adaptador)

**Directorio:** `backend/adapters/`

```python
# base.py — Interfaz abstracta
class BaseStoreAdapter(ABC):
    @abstractmethod
    def test_connection(self) -> ConnectionTestResult: ...
    @abstractmethod
    def fetch_products(self, page, per_page) -> List[RemoteProduct]: ...
    @abstractmethod
    def push_product_update(self, remote_id, updates) -> bool: ...

# woocommerce.py — Implementación concreta
class WooCommerceAdapter(BaseStoreAdapter):
    def fetch_products(self, page=1, per_page=50):
        resp = self._request("GET", "products", params={...})
        return [self._parse_product(p) for p in resp.json()]

# __init__.py — Factory
def get_adapter(platform: str, config: dict) -> BaseStoreAdapter:
    adapters = {
        "woocommerce": WooCommerceAdapter,
        "shopify": ShopifyAdapter,
        "bsale": BsaleAdapter,
        "custom": CustomAPIAdapter,
    }
    return adapters[platform](config)
```

**¿Por qué?**

- **Principio Abierto/Cerrado (OCP)**: Agregar una nueva plataforma (ej. Mercado Libre, PrestaShop) requiere solo crear una nueva clase que herede de `BaseStoreAdapter`. No se modifica ningún código existente.
- **Polimorfismo**: El motor de sync no sabe (ni necesita saber) con qué plataforma está interactuando. Solo llama `adapter.fetch_products()` y recibe objetos `RemoteProduct` normalizados.
- **Testabilidad**: Se puede crear un `MockAdapter` para pruebas sin necesidad de conectarse a APIs reales.
- **Complejidad encapsulada**: Cada plataforma tiene su propia autenticación (WooCommerce usa Basic Auth, Shopify usa tokens en headers, Bsale usa `access_token` en header), sus propios formatos de datos y su propia paginación. Todo esto queda encapsulado dentro de cada adaptador.

**¿Es esto sobre-ingeniería?** No. Éste es un caso donde la abstracción existe porque hay 4 implementaciones reales con diferencias significativas. Sin ella, tendríamos condicionales `if platform == "woocommerce"` dispersos por todo el código de sync.

---

### 6.4 — Factory Pattern (Patrón Fábrica)

**Archivo:** `backend/adapters/__init__.py`

```python
def get_adapter(platform: str, config: dict) -> BaseStoreAdapter:
    adapters = {
        "woocommerce": WooCommerceAdapter,
        "shopify": ShopifyAdapter,
        "bsale": BsaleAdapter,
        "custom": CustomAPIAdapter,
    }
    adapter_class = adapters.get(platform)
    if not adapter_class:
        raise ValueError(f"Unsupported platform: {platform}")
    return adapter_class(config)
```

**¿Por qué?**

- **Desacoplamiento**: El código consumidor (endpoints en `main.py`) no importa ni instancia directamente las clases de adaptadores. Solo llama `get_adapter("shopify", config)`.
- **Punto único de registro**: Agregar un nuevo adaptador requiere solo registrarlo en el diccionario `adapters`. Es un cambio de una línea.
- **Inversión de dependencia (DIP)**: Los endpoints dependen de la abstracción (`BaseStoreAdapter`), no de implementaciones concretas.

**Nota pragmática:** Es una función simple, no una `AbstractFactoryBuilder`. El Factory como función de 8 líneas es la implementación correcta para nuestro caso. Si tuviéramos factories que necesitan configuración propia, escalaríamos a clases.

---

### 6.5 — Normalized Data Object Pattern

**Archivo:** `backend/adapters/base.py`

```python
@dataclass
class RemoteProduct:
    remote_id: str
    name: str
    canonical_url: str       # ← Identificador universal entre sistemas
    sku: Optional[str]
    price: Optional[str]
    stock: Optional[str]
    # ... campos normalizados
    raw_data: Optional[dict]  # ← Snapshot completo para auditoría
```

**¿Por qué?**

- **Normalización de datos heterogéneos**: WooCommerce llama al nombre `name`, Shopify lo llama `title`, Bsale lo llama `name` también pero con estructura diferente. `RemoteProduct` unifica todo esto en un formato estándar.
- **URL canónica como identificador**: A diferencia de IDs internos (que pueden colisionar entre sistemas), la URL canónica es:
  - **Única**: Cada producto tiene su propia URL.
  - **Estable**: No cambia cuando se migra de servidor o se actualiza el sistema.
  - **Legible**: Un humano puede verificar visualmente si dos productos son el mismo.
- **Preservación del dato original**: El campo `raw_data` guarda el JSON completo del producto remoto, permitiendo auditoría, debugging, y acceso a campos que quizás no mapeamos inicialmente.

---

## 7. Patrones Estructurales

### 7.1 — Layered Architecture (Arquitectura en Capas)

```
┌───────────────────────────────────────────────────┐
│                  Presentación                      │  ← Frontend (React/Next.js)
│   Componentes, páginas, estado local, i18n        │
├───────────────────────────────────────────────────┤
│                  API / Controlador                 │  ← FastAPI endpoints (main.py)
│   Routing, validación, serialización              │
├───────────────────────────────────────────────────┤
│                  Lógica de Negocio                 │  ← Adapters, sync engine
│   Reglas de harmonización, adaptadores, cola      │
├───────────────────────────────────────────────────┤
│                  Acceso a Datos                    │  ← SQLAlchemy ORM (models.py)
│   Queries, transacciones, migraciones             │
├───────────────────────────────────────────────────┤
│                  Persistencia                      │  ← SQLite (sql_app.db)
│   Almacenamiento físico                           │
└───────────────────────────────────────────────────┘
```

**¿Por qué?**

- **Cada capa tiene una responsabilidad clara**: No se mezcla lógica de presentación con acceso a datos.
- **Reemplazabilidad**: Cada capa puede ser sustituida sin afectar a las demás (ej. cambiar SQLite por PostgreSQL, o React por Vue).
- **Testabilidad**: Cada capa puede probarse de forma aislada.

**Nota honesta:** En la práctica, las capas de "API/Controlador" y "Lógica de Negocio" viven juntas en `main.py`. Esto es deliberado para nuestra fase actual. Separaremos cuando la complejidad lo justifique (ver sección 4, Triggers de Evolución).

---

### 7.2 — Monorepo Structure

```
DBDesambiguador/
├── backend/       ← Módulo Python independiente
├── frontend/      ← Módulo Node.js independiente  
├── docs/          ← Documentación compartida
└── scripts/       ← Utilidades transversales
```

**¿Por qué?**

- **Cohesión del proyecto**: Todo el código vive en un solo repositorio, facilitando los PRs que involucran cambios full-stack.
- **Versionado atómico**: Un commit puede incluir cambios coordinados en backend y frontend, evitando desincronización.
- **Simplicidad operativa**: Un solo `git clone` obtiene todo lo necesario para ejecutar la aplicación.

---

## 8. Patrones de Integración

### 8.1 — Human-in-the-Loop (Supervisión Humana)

```
    Pull de         Cola de            Revisión         Aplicación
    Tienda   ──►   Pendientes   ──►   Humana    ──►   de Cambios
                  (SyncQueueItem)     (Approve/        (status: applied)
                                       Reject)
```

**¿Por qué?**

- **Control de calidad**: Los datos de tiendas externas pueden contener errores, duplicados o formatos inconsistentes. Un humano revisa antes de integrar.
- **Reversibilidad**: Si un cambio se aprueba por error, existe un registro claro de quién aprobó qué y cuándo.
- **Contexto de negocio**: El sistema no puede decidir automáticamente si un precio de $0.00 es un error o una promoción —solo un humano con contexto de negocio puede hacerlo.
- **Auditoría**: Cada acción queda registrada en `SyncLog`, creando un trail completo de todas las operaciones de sincronización.

**¿No deberíamos automatizarlo?** Eventualmente sí, para cambios de bajo riesgo (ej. actualización de stock). Pero **primero observamos los patrones** a través de la cola manual, luego generamos las reglas automáticas desde datos reales. Automatizar sin datos es adivinar.

---

### 8.2 — Canonical URL Mapping (Mapeo por URL Canónica)

```
  Base de Datos Local              Tienda Remota
  ┌──────────────┐                ┌──────────────┐
  │ id: 4523     │                │ id: prod_89  │
  │ sku: ABC-001 │    mapeo vía   │ sku: abc001  │
  │              │ ◄────────────► │              │
  │              │  canonical_url │ permalink:   │
  │              │  https://...   │ https://...  │
  └──────────────┘                └──────────────┘
```

**¿Por qué NO mapear por ID interno?**

| Criterio | ID Interno | URL Canónica |
|----------|-----------|--------------|
| Unicidad entre sistemas | ❌ ID 123 puede existir en ambos | ✅ URL es globalmente única |
| Persistencia | ⚠️ Puede cambiar en migraciones | ✅ Se mantiene estable |
| Legibilidad | ❌ "prod_89" no dice nada | ✅ "/product/laptop-hp-15" es descriptivo |
| Verificabilidad | ❌ Requiere acceso a BD | ✅ Se puede abrir en navegador |
| Multi-plataforma | ❌ Formatos incompatibles | ✅ Estándar web universal |

**¿Por qué NO mapear por SKU?**

- Los SKU no siempre son consistentes entre sistemas (mayúsculas, guiones, espacios).
- Algunos productos no tienen SKU.
- Los SKU pueden reutilizarse para productos diferentes en distintas plataformas.

---

### 8.3 — Change Detection Pattern (Detección de Cambios)

```python
# En el pull, se comparan campos críticos:
if existing.remote_name != rp.name:
    changes.append(("name", existing.remote_name, rp.name))
if existing.remote_price != rp.price:
    changes.append(("price", existing.remote_price, rp.price))
```

**¿Por qué?**

- **Eficiencia**: Solo se crean items en la cola cuando hay cambios reales, evitando ruido.
- **Granularidad**: Cada cambio de campo se registra individualmente, permitiendo aprobar el cambio de precio pero rechazar el cambio de nombre.
- **Idempotencia**: Múltiples pulls no crean duplicados (`already_pending` check).

---

## 9. Patrones de Frontend

### 9.1 — File-Based Routing (Next.js App Router)

```
frontend/app/
├── page.tsx              → /           (Catálogo)
├── analytics/page.tsx    → /analytics
├── integrations/
│   ├── page.tsx          → /integrations
│   └── [id]/page.tsx     → /integrations/:id  (ruta dinámica)
├── settings/page.tsx     → /settings
└── ...
```

**¿Por qué?**

- **Convención sobre configuración**: La estructura del filesystem define las rutas. No es necesario un archivo de configuración de routing.
- **Colocación**: Cada ruta tiene su código en su propia carpeta, facilitando la navegación del proyecto.
- **Code splitting automático**: Next.js solo carga el JavaScript necesario para cada página.

---

### 9.2 — Context Pattern para Estado Global

**Archivos:** `contexts/LanguageContext.tsx`, `components/SidebarProvider.tsx`

```tsx
// LanguageContext — i18n
const { t, language, setLanguage } = useLanguage();

// SidebarProvider — estado del sidebar
const { collapsed, toggle } = useSidebar();
```

**¿Por qué?**

- **Prop drilling prevention**: Sin Context, tendríamos que pasar `language` y `collapsed` a través de 5+ niveles de componentes.
- **Single source of truth**: El idioma y el estado del sidebar se gestionan en un solo lugar.
- **Escalabilidad controlada**: Para estado más complejo (ej. caché de queries), se podría migrar a Zustand o TanStack Query sin cambiar la API de consumo.

**¿Por qué no Zustand o Redux desde el inicio?** Porque React Context resuelve nuestros 2 casos de uso (idioma, sidebar) sin dependencias extra. Agregar una librería de state management para 2 valores sería sobre-ingeniería textbook.

---

### 9.3 — Patrón de Componentes Presentacionales

```
components/
├── Sidebar.tsx             ← Navegación
├── SidebarProvider.tsx     ← Estado del sidebar
├── ProductTable.tsx        ← Tabla de productos (editable)
├── ProductVariantView.tsx  ← Vista de variantes
└── ThemeToggle.tsx         ← Switch dark/light
```

**¿Por qué?**

- **Reutilización**: `ProductTable` se usa tanto en la página principal como potencialmente en otras vistas.
- **Encapsulamiento**: Cada componente maneja su propia lógica de UI sin depender del contexto de la página.
- **Facilidad de testing**: Un componente aislado es más fácil de probar que una página completa.

---

## 10. Patrones de Datos

### 10.1 — Column Mapping (Mapeo de Columnas)

**Archivo:** `backend/main.py`

```python
COLUMN_MAPPING = {
    "Nombre del Producto": "product_name",
    "Clasificación": "classification",
    "Tipo de Producto": "product_type",
    # ...60+ mapeos
}
```

**¿Por qué?**

- **Desacoplamiento de formato externo e interno**: Los archivos Excel pueden tener headers en español con acentos y espacios. Internamente usamos snake_case en inglés.
- **Punto único de verdad**: Si un nombre de columna cambia en el Excel fuente, solo hay que actualizar un mapeo.
- **Bidireccionalidad**: `EXPORT_COLUMN_MAPPING` (inverso) se genera automáticamente para exportar.

---

### 10.2 — Harmonization Pipeline con Undo/Redo

```
Paso 1: Normalizar        Paso 2: Corregir        Paso 3: Estandarizar
marcas en minúsculas  →  typos con Levenshtein  →  formatos de SKU
        │                        │                        │
        └─── Log + Changes ──── └─── Log + Changes ──── └─── Log + Changes
                                    (cada paso reversible)
```

**¿Por qué?**

- **Trazabilidad completa**: Cada paso de harmonización registra exactamente qué valores cambiaron, en qué registros, y cuándo.
- **Reversibilidad**: Si un paso introduce errores, se puede hacer `undo` sin perder el trabajo de otros pasos.
- **Independencia de pasos**: Cada paso puede ejecutarse o revertirse individualmente, sin afectar a los demás.

---

### 10.3 — Internationalization (i18n) por Diccionario

**Archivo:** `frontend/app/i18n/translations.ts`

```typescript
export const translations = {
    en: { 'nav.home': 'Product Catalog', ... },
    es: { 'nav.home': 'Catálogo de Productos', ... },
};
```

**¿Por qué?**

- **Simplicidad**: Para 2 idiomas con ~30 claves, un archivo de diccionario es más ligero que una librería completa como `react-i18next`.
- **Type safety**: TypeScript verifica que las claves existen en ambos idiomas en tiempo de compilación.
- **Extensibilidad**: Si el proyecto crece a más de 3 idiomas o 100+ claves, migrar a `react-i18next` o `next-intl` es un refactor localizado.

---

## 11. Decisiones Técnicas Clave

### ¿Por qué FastAPI (y no Django, Flask, Express)?

| Criterio | FastAPI | Django | Flask |
|----------|---------|--------|-------|
| Validación automática | ✅ Pydantic nativo | ⚠️ Requiere DRF | ❌ Manual |
| Documentación API | ✅ Swagger auto | ⚠️ Con DRF | ❌ Plugin |
| Performance | ✅ ASGI async-ready | ⚠️ WSGI | ⚠️ WSGI |
| Curva de aprendizaje | ✅ Mínima | ⚠️ Mayor (ORM propio) | ✅ Mínima |
| Ecosistema Python | ✅ Compatible total | ✅ Extenso | ✅ Compatible |

**Decisión**: FastAPI ofrece el mejor balance entre productividad, validación y documentación automática para una API REST de gestión de datos.

### ¿Por qué SQLite (y no PostgreSQL)?

- **Fase actual**: Herramienta local/mono-usuario. SQLite no requiere configurar un servidor de BD.
- **Portabilidad**: La BD es un archivo (`sql_app.db`) que se puede copiar, respaldar o compartir fácilmente.
- **Preparación para escalar**: El ORM (SQLAlchemy) abstrae el motor. Migrar a PostgreSQL requiere solo cambiar la URL de conexión, sin tocar queries.

### ¿Por qué Next.js (y no Vite + React, Angular)?

- **App Router**: Routing declarativo por filesystem, sin configuración.
- **SSR/SSG**: Capacidad de renderizado del lado del servidor (útil si la app evoluciona a multi-usuario).
- **Full-stack ready**: Si en el futuro necesitamos API routes internas o middleware, Next.js lo soporta nativamente.

---

## 12. Diagrama de Flujo de Datos

### Flujo de sincronización con tienda

```
                           ┌─────────────────────┐
                           │   Tienda Virtual     │
                           │  (WooCommerce,       │
                           │   Shopify, Bsale)    │
                           └──────────┬──────────┘
                                      │
                              API REST (fetch)
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │   Adapter Layer      │
                           │  (WooCommerceAdapter │
                           │   ShopifyAdapter...) │
                           └──────────┬──────────┘
                                      │
                             RemoteProduct normalizado
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │      Canonical URL Matching       │
                    │  ¿Existe mapeo para esta URL?     │
                    └──────┬───────────────┬────────────┘
                           │               │
                      NO (nuevo)      SÍ (existente)
                           │               │
                           ▼               ▼
                  ┌──────────────┐  ┌──────────────────┐
                  │ Crear Mapping │  │ Detectar Cambios  │
                  │ + Queue Item  │  │ (campo por campo)  │
                  │ "new_product" │  │ → Queue Items      │
                  └──────┬───────┘  └────────┬───────────┘
                         │                   │
                         └─────────┬─────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │   Cola de Revisión   │
                        │   (SyncQueueItem)    │
                        │   status: "pending"  │
                        └──────────┬──────────┘
                                   │
                           Revisión humana
                          (approve / reject)
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │   SyncLog            │
                        │   (historial)        │
                        └─────────────────────┘
```

---

## 13. Anti-Patrones: Lo Que Decidimos NO Hacer

Tan importante como documentar lo que hacemos es documentar lo que **decidimos no hacer** y por qué. Estas decisiones son activas, no omisiones accidentales.

### 13.1 — NO microservicios

```
  ❌ Lo que NO hacemos:                    ✅ Lo que SÍ hacemos:

  ┌─────────┐  ┌─────────┐               ┌──────────────────────────┐
  │ Product │  │  Sync   │               │                          │
  │ Service │  │ Service │               │   Un proceso FastAPI     │
  │  :8001  │  │  :8002  │               │   con módulos internos   │
  └────┬────┘  └────┬────┘               │   bien organizados       │
       │            │                     │                          │
  ┌────┴────┐  ┌────┴────┐               │   main.py (endpoints)    │
  │  Auth   │  │  Queue  │               │   adapters/ (integración)│
  │ Service │  │ Service │               │   models.py (datos)      │
  │  :8003  │  │  :8004  │               │   schemas.py (validación)│
  └─────────┘  └─────────┘               └──────────────────────────┘
  
  4 procesos, 4 puertos,                  1 proceso, 1 puerto,
  comunicación inter-servicio,             llamadas de función,
  service discovery, circuit              debugging con print(),
  breakers, distributed tracing...         hot reload instantáneo.
```

**¿Por qué?** Los microservicios resuelven problemas de *escala organizacional* (múltiples equipos, despliegue independiente). Nosotros somos un equipo pequeño con un solo producto. La comunicación entre módulos es una llamada de función (nanosegundos), no un HTTP request (milisegundos).

**Cuándo reconsiderar:** Cuando tengamos > 3 desarrolladores con conflictos frecuentes en las mismas partes del código, O cuando un módulo necesite escalar independientemente (ej. el sync consume muchos recursos pero la API de lectura no).

---

### 13.2 — NO Event Sourcing / CQRS

**¿Qué son?** Almacenar cada cambio como un evento inmutable y reconstruir el estado actual reproduciéndolos.

**¿Por qué no?** Nuestro `SyncLog` + `HarmonizationLog` + `SyncQueueItem` proveen auditoría completa sin la complejidad de reconstrucción de estado. El estado actual vive en las tablas directamente.

**Cuándo reconsiderar:** Si necesitamos "viajar en el tiempo" (ver el estado de un producto hace 3 meses) o si la auditoría necesita ser legalmente inmutable.

---

### 13.3 — NO GraphQL

**¿Por qué no?** GraphQL brilla cuando:
- El frontend necesita combinaciones flexibles de datos (no es nuestro caso — cada vista tiene su endpoint dedicado).
- Hay over-fetching severo (no es nuestro caso — los endpoints retornan solo lo necesario).
- Múltiples clientes consumen la API de formas distintas (solo tenemos un cliente).

**Cuándo reconsiderar:** Si el frontend empieza a hacer 3+ requests secuenciales para construir una sola vista, o si otros clientes (móvil, terceros) empiezan a consumir la API.

---

### 13.4 — NO Message Queue (RabbitMQ, Kafka)

**¿Por qué no?** Las operaciones de sync son síncronas y de duración manejable (< 30 segundos para 50 productos). No hay necesidad de procesamiento asíncrono distribuido.

**Cuándo reconsiderar:** Si un pull de 1000+ productos tarda > 60 segundos y necesita ejecutarse en background, o si necesitamos procesar webhooks de tiendas en tiempo real.

---

### 13.5 — NO Container Orchestration (Kubernetes)

**¿Por qué no?** La aplicación tiene 2 procesos (backend + frontend) y una BD de archivo. Docker Compose es suficiente si necesitamos containerización.

**Cuándo reconsiderar:** Si necesitamos auto-scaling, zero-downtime deployments, o múltiples instancias del backend.

---

## 14. Guía de Decisión para Nuevas Features

### Antes de implementar cualquier feature nueva, hazte estas preguntas:

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  1. ¿CUÁL ES EL PROBLEMA?                                       │
│     Describe el problema en una oración sin mencionar            │
│     la solución. Si no puedes, quizás no hay problema.           │
│                                                                  │
│  2. ¿CUÁL ES LA SOLUCIÓN MÁS SIMPLE?                            │
│     ¿Se puede resolver con una función? ¿Un campo en la BD?     │
│     ¿Un componente? Empieza por ahí.                             │
│                                                                  │
│  3. ¿QUÉ CONTRATO ESTABLEZCO?                                   │
│     ¿Estoy creando un endpoint público? ¿Un schema de BD?       │
│     ¿Una prop de componente? Estos contratos son difíciles       │
│     de cambiar — diseñarlos bien SÍ vale la inversión.           │
│                                                                  │
│  4. ¿QUÉ PRECEDENTE CREO?                                       │
│     Si lo hago así, ¿el equipo seguirá este patrón?             │
│     ¿Es un patrón que quiero que se repita?                      │
│                                                                  │
│  5. ¿PUEDO BORRARLO FÁCILMENTE?                                 │
│     El mejor código es el que se puede eliminar sin              │
│     efectos colaterales. Si tu abstracción no se puede           │
│     borrar limpiamente, es demasiado acoplada.                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Principios SOLID Aplicados

| Principio | Implementación | Nota pragmática |
|-----------|----------------|-----------------|
| **S** – Single Responsibility | Cada adaptador maneja solo su plataforma. Cada componente React maneja solo su UI. | `main.py` tiene múltiples responsabilidades *por ahora*. Es la decisión correcta para esta fase. |
| **O** – Open/Closed | Nuevas plataformas se agregan creando nuevas clases, sin modificar las existentes. | Aplicado donde hay variabilidad real (adapters). No aplicado donde no la hay (endpoints). |
| **L** – Liskov Substitution | Cualquier adaptador puede sustituir a otro donde se espere un `BaseStoreAdapter`. | Verificado: el motor de sync funciona igual con cualquier adaptador. |
| **I** – Interface Segregation | `BaseStoreAdapter` define solo los métodos que TODOS los adaptadores necesitan. | Si un adaptador necesita un método especial, va en la subclase — no en la interfaz base. |
| **D** – Dependency Inversion | Los endpoints dependen de `BaseStoreAdapter` (abstracción), no de `WooCommerceAdapter` (implementación concreta). | Implementado vía Factory. No usamos inyección de dependencias formal porque no la necesitamos. |

---

## Resumen Ejecutivo

```
┌────────────────────────────────────────────────────────────────┐
│                  NUESTRO EQUILIBRIO                             │
│                                                                │
│   ✅ Débil acoplamiento              — SÍ, entre módulos      │
│   ✅ Fuerte interoperabilidad        — SÍ, vía REST/JSON      │
│   ✅ Contratos de servicio           — SÍ, vía Pydantic       │
│   ✅ Abstracción donde hay variación — SÍ, Adapter Pattern    │
│   ✅ Auditoría y trazabilidad        — SÍ, SyncLog + Queue    │
│                                                                │
│   ❌ Microservicios                  — NO, innecesarios       │
│   ❌ Event Bus / CQRS                — NO, complejidad > valor│
│   ❌ GraphQL                         — NO, resuelve problemas │
│                                         que no tenemos         │
│   ❌ Container orchestration         — NO, escala insuficiente│
│   ❌ Cache distribuido               — NO, latencia < 1ms     │
│                                                                │
│   Filosofía: Cada patrón justifica su existencia.              │
│   Si no resuelve un problema real, no se implementa.           │
│   Si luego lo necesitamos, lo implementaremos — con datos.     │
└────────────────────────────────────────────────────────────────┘
```

---

*Este documento se actualiza conforme evoluciona la arquitectura del proyecto. Cada actualización debe incluir el trigger que motivó el cambio.*
