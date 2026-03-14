from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float
from .database import Base


class UniversalEntity(Base):
    __tablename__ = "raw_entities"

    id = Column(Integer, primary_key=True, index=True)

    # Universal fields
    domain = Column(String, default="default", index=True)
    entity_type = Column(String, nullable=True, index=True)

    primary_label = Column(String, index=True)
    secondary_label = Column(String, nullable=True)
    canonical_id = Column(String, index=True, nullable=True)

    attributes_json = Column(Text, default="{}")

    # Metadata
    validation_status = Column(String, default="pending", index=True)
    normalized_json = Column(Text, nullable=True)

    # Enrichment
    enrichment_doi = Column(String, nullable=True)
    enrichment_citation_count = Column(Integer, default=0)
    enrichment_concepts = Column(Text, nullable=True)
    enrichment_source = Column(String, nullable=True)
    enrichment_status = Column(String, default="none", index=True)

    # Provenance
    source = Column(String, default="user")

# Keep alias so existing imports of models.RawEntity still work
RawEntity = UniversalEntity


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"

    id          = Column(Integer, primary_key=True, index=True)
    source_id   = Column(Integer, index=True)   # FK to raw_entities.id
    target_id   = Column(Integer, index=True)   # FK to raw_entities.id
    relation_type = Column(String, index=True)  # cites | authored-by | belongs-to | related-to
    weight      = Column(Float, default=1.0)
    notes       = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class NormalizationRule(Base):
    __tablename__ = "normalization_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    field_name = Column(String, index=True) # e.g., "brand_lower"
    original_value = Column(String, index=True) # e.g., "mikrosoft"
    normalized_value = Column(String) # e.g., "Microsoft"
    is_regex = Column(Boolean, default=False)


class HarmonizationLog(Base):
    __tablename__ = "harmonization_logs"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(String, index=True)
    step_name = Column(String)
    records_updated = Column(Integer)
    fields_modified = Column(Text)
    executed_at = Column(DateTime)
    details = Column(Text, nullable=True)
    reverted = Column(Boolean, default=False)


class HarmonizationChangeRecord(Base):
    __tablename__ = "harmonization_change_records"

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(Integer, index=True)
    record_id = Column(Integer, index=True)
    field = Column(String)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)


class StoreConnection(Base):
    __tablename__ = "store_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)                    # Human-friendly label, e.g. "Mi Tienda WooCommerce"
    platform = Column(String, index=True)                # woocommerce | shopify | bsale | custom
    base_url = Column(String)                            # e.g. https://mitienda.com
    api_key = Column(String, nullable=True)               # Consumer key / API key
    api_secret = Column(String, nullable=True)            # Consumer secret / API secret
    access_token = Column(String, nullable=True)          # For OAuth-based platforms (Shopify)
    custom_headers = Column(Text, nullable=True)          # JSON string for custom API headers
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime)
    entity_count = Column(Integer, default=0)            # Cached count of mapped products
    sync_direction = Column(String, default="bidirectional")  # pull | push | bidirectional
    notes = Column(Text, nullable=True)


class StoreSyncMapping(Base):
    __tablename__ = "store_sync_mappings"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True)               # FK to store_connections.id
    local_entity_id = Column(Integer, index=True)       # FK to raw_entities.id
    remote_entity_id = Column(String, nullable=True)    # ID in the remote store
    canonical_url = Column(String, index=True)            # The canonical URL used for mapping
    remote_sku = Column(String, nullable=True)
    remote_name = Column(String, nullable=True)
    remote_price = Column(String, nullable=True)
    remote_stock = Column(String, nullable=True)
    remote_status = Column(String, nullable=True)
    remote_data_json = Column(Text, nullable=True)       # Full remote product data snapshot
    sync_status = Column(String, default="pending")      # pending | synced | conflict | error
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime)


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True)               # FK to store_connections.id
    action = Column(String)                              # pull | push | map | unmap
    status = Column(String)                              # success | error | partial
    records_affected = Column(Integer, default=0)
    details = Column(Text, nullable=True)                # JSON with details
    executed_at = Column(DateTime)


class SyncQueueItem(Base):
    __tablename__ = "sync_queue"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True)               # FK to store_connections.id
    mapping_id = Column(Integer, nullable=True, index=True)  # FK to store_sync_mappings.id
    direction = Column(String)                            # pull | push
    entity_name = Column(String, nullable=True)          # For display convenience
    canonical_url = Column(String, nullable=True)
    field = Column(String)                                # Which field changed
    local_value = Column(Text, nullable=True)
    remote_value = Column(Text, nullable=True)
    status = Column(String, default="pending", index=True) # pending | approved | rejected | applied
    created_at = Column(DateTime)
    resolved_at = Column(DateTime, nullable=True)

class AIIntegration(Base):
    """
    Phase 5: Store settings for Semantic RAG architectures (LLMs and Vector DBs).
    Supports Cloud (OpenAI, Claude, DeepSeek, XAI, Google) and Local variants.
    """
    __tablename__ = "ai_integrations"

    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String, index=True, unique=True)  # openai | anthropic | xai | deepseek | google | local
    base_url = Column(String, nullable=True)                 # for local/custom endpoints
    api_key = Column(String, nullable=True)                  # Bring Your Own Key (BYOK)
    model_name = Column(String, nullable=True)               # e.g., gpt-4o, claude-3.5-sonnet, r1, llama3
    is_active = Column(Boolean, default=False)               # which provider is the active one?
    created_at = Column(DateTime)


# ── RBAC: Users ────────────────────────────────────────────────────────────

class User(Base):
    """
    Platform user with a fixed role (super_admin | admin | editor | viewer).
    Credentials are stored in this table; no more env-var-only auth.
    """
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(50), unique=True, index=True, nullable=False)
    email           = Column(String(255), unique=True, index=True, nullable=True)
    password_hash   = Column(String, nullable=False)
    role            = Column(String, nullable=False, default="viewer")
    is_active       = Column(Boolean, default=True)
    created_at      = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())
    failed_attempts = Column(Integer, default=0)
    locked_until    = Column(String, nullable=True)  # ISO datetime string; None = not locked
    avatar_url      = Column(Text, nullable=True)       # data URL (base64), Sprint 58
    display_name    = Column(String(100), nullable=True)  # optional full name, Sprint 59
    bio             = Column(Text, nullable=True)          # short bio, Sprint 59


# ── Authority Resolution Layer ──────────────────────────────────────────────

class AuthorityRecord(Base):
    """
    Stores candidates returned by the Authority Resolution Layer.
    Each record links a local field value to an entry in an external
    knowledge authority (Wikidata, VIAF, ORCID, DBpedia, OpenAlex).
    status: pending | confirmed | rejected
    """
    __tablename__ = "authority_records"

    id               = Column(Integer, primary_key=True, index=True)
    field_name       = Column(String, index=True)         # e.g. "brand_capitalized"
    original_value   = Column(String, index=True)         # local value that was queried
    authority_source = Column(String, index=True)         # wikidata | viaf | orcid | dbpedia | openalex
    authority_id     = Column(String)                     # Q2283 | viaf/20069448 | 0000-0001-… etc.
    canonical_label  = Column(String)                     # official canonical form from the authority
    aliases          = Column(Text, nullable=True)        # JSON array of known aliases
    description      = Column(Text, nullable=True)        # short description from authority
    confidence       = Column(Float, default=0.0)         # 0.0–1.0 fuzzy similarity score
    uri              = Column(String, nullable=True)       # URL of the authority record
    status           = Column(String, default="pending", index=True)
    created_at       = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())
    confirmed_at     = Column(String, nullable=True)
    # Sprint 16 — scoring engine
    resolution_status = Column(String, default="unresolved", index=True)  # exact_match | probable_match | ambiguous | unresolved
    score_breakdown   = Column(Text, nullable=True)   # JSON: {identifiers, name, affiliation, coauthorship, topic}
    evidence          = Column(Text, nullable=True)   # JSON array of signal strings
    merged_sources    = Column(Text, nullable=True)   # JSON array of "source:id" refs merged into this record


class Webhook(Base):
    """
    Outbound webhook registration.
    events: JSON array of action strings, e.g. ["upload", "entity.delete"]
    secret: optional HMAC-SHA256 signing key sent in X-UKIP-Signature header
    """
    __tablename__ = "webhooks"

    id                = Column(Integer, primary_key=True, index=True)
    url               = Column(String, nullable=False)
    events            = Column(Text, nullable=False)           # JSON array
    secret            = Column(String, nullable=True)
    is_active         = Column(Boolean, default=True)
    created_at        = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_triggered_at = Column(DateTime, nullable=True)
    last_status       = Column(Integer, nullable=True)         # HTTP status of last delivery


class WebhookDelivery(Base):
    """
    Sprint 60: Logs each outbound webhook delivery attempt.
    Enables the delivery history timeline in the Webhooks UI Panel.
    """
    __tablename__ = "webhook_deliveries"

    id          = Column(Integer, primary_key=True, index=True)
    webhook_id  = Column(Integer, index=True, nullable=False)   # FK webhooks.id
    event       = Column(String, nullable=False)                # e.g. "upload", "entity.delete"
    url         = Column(String, nullable=False)                # destination URL at time of delivery
    status_code = Column(Integer, nullable=True)                # HTTP status (0 = network error)
    response_body = Column(Text, nullable=True)                 # first 500 chars of response
    latency_ms  = Column(Integer, nullable=True)                # round-trip time in milliseconds
    error       = Column(String, nullable=True)                 # exception message if delivery failed
    success     = Column(Boolean, default=False)                # True if 2xx
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class LinkDismissal(Base):
    """Stores entity pairs the user has explicitly marked as 'not a duplicate'."""
    __tablename__ = "link_dismissals"

    id          = Column(Integer, primary_key=True, index=True)
    entity_a_id = Column(Integer, index=True, nullable=False)   # always the smaller ID
    entity_b_id = Column(Integer, index=True, nullable=False)   # always the larger ID
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, index=True)
    action      = Column(String, index=True)          # CREATE | UPDATE | DELETE (Sprint 51+)
    entity_type = Column(String, nullable=True)       # "entity", "authority_record", "rule", …
    entity_id   = Column(Integer, nullable=True)
    user_id     = Column(Integer, nullable=True)
    details     = Column(Text, nullable=True)         # JSON blob with extra context
    # Sprint 51 — HTTP-level columns added via migration
    username    = Column(String, nullable=True, index=True)  # JWT "sub" claim
    endpoint    = Column(String, nullable=True)              # /entities/42
    method      = Column(String, nullable=True)              # POST | PUT | DELETE
    status_code = Column(Integer, nullable=True)
    ip_address  = Column(String, nullable=True)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


# ── Sprint 42: Collaborative Annotations ────────────────────────────────────

class Annotation(Base):
    """
    Threaded comment attached to a RawEntity or AuthorityRecord.
    parent_id enables one-level reply threading.
    author_name is denormalized for display without a JOIN.
    """
    __tablename__ = "annotations"

    id           = Column(Integer, primary_key=True, index=True)
    entity_id    = Column(Integer, nullable=True, index=True)    # FK raw_entities.id
    authority_id = Column(Integer, nullable=True, index=True)    # FK authority_records.id
    parent_id    = Column(Integer, nullable=True)                # FK annotations.id (replies)
    author_id    = Column(Integer, nullable=False)               # FK users.id
    author_name  = Column(String, nullable=False)               # denormalized
    content      = Column(Text, nullable=False)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))


# ── Sprint 43: Email Notification Settings (singleton, id=1) ────────────────

class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id                         = Column(Integer, primary_key=True, default=1)
    smtp_host                  = Column(String, default="")
    smtp_port                  = Column(Integer, default=587)
    smtp_user                  = Column(String, default="")
    smtp_password              = Column(String, default="")  # stored encrypted via Fernet
    from_email                 = Column(String, default="")
    recipient_email            = Column(String, default="")
    enabled                    = Column(Boolean, default=False)
    notify_on_enrichment_batch = Column(Boolean, default=True)
    notify_on_authority_confirm= Column(Boolean, default=True)


# ── Sprint 44: Custom Branding Settings (singleton, id=1) ───────────────────

class BrandingSettings(Base):
    __tablename__ = "branding_settings"

    id            = Column(Integer, primary_key=True, default=1)
    platform_name = Column(String, default="UKIP")
    logo_url      = Column(String, default="")
    accent_color  = Column(String, default="#6366f1")   # indigo-500
    footer_text   = Column(String, default="Universal Knowledge Intelligence Platform")


# ── Phase 10 Sprint 46: Artifact Templates ────────────────────────────────────

class ArtifactTemplate(Base):
    """
    Saved report configurations. 4 built-in templates are seeded in lifespan.
    User-created templates have is_builtin=False and can be deleted.
    sections stores a JSON array of section name strings.
    """
    __tablename__ = "artifact_templates"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String, nullable=False)
    description   = Column(String, default="")
    sections      = Column(Text, nullable=False)       # JSON: ["entity_stats", ...]
    default_title = Column(String, default="")
    is_builtin    = Column(Boolean, default=False)
    created_by    = Column(Integer, nullable=True)     # FK users.id (nullable for built-ins)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Phase 11 Sprint 48: Analysis Context Sessions ─────────────────────────────

class AnalysisContext(Base):
    """
    Persisted domain context snapshot. Stores the assembled domain state
    (entity stats, gaps, topics, schema) at a point in time.
    Used by the Context Engineering Layer and context-aware RAG.
    """
    __tablename__ = "analysis_contexts"

    id               = Column(Integer, primary_key=True, index=True)
    domain_id        = Column(String, nullable=False, index=True)
    user_id          = Column(Integer, nullable=True)     # FK users.id (nullable for system)
    label            = Column(String, default="")         # user-defined name
    context_snapshot = Column(Text, nullable=False)       # JSON from ContextEngine
    notes            = Column(Text, nullable=True)
    pinned           = Column(Boolean, default=False)
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Sprint 56: Notification Center read-state ─────────────────────────────────

class UserNotificationState(Base):
    """
    One row per user tracking when they last read all their notifications.
    last_read_at is used as the threshold: audit log entries created after
    this timestamp are considered "unread".
    """
    __tablename__ = "user_notification_states"

    user_id      = Column(Integer, primary_key=True)   # FK users.id
    last_read_at = Column(DateTime, nullable=True)     # NULL = never read anything


# ── Sprint 61: Scheduled Imports ───────────────────────────────────────────────

class ScheduledImport(Base):
    """
    Cron-based automated ingestion from a configured store connection.
    interval_minutes is a simple interval approach (no full cron parser needed).
    """
    __tablename__ = "scheduled_imports"

    id              = Column(Integer, primary_key=True, index=True)
    store_id        = Column(Integer, index=True, nullable=False)  # FK store_connections.id
    name            = Column(String, nullable=False)               # human label
    interval_minutes = Column(Integer, nullable=False, default=60) # run every N minutes
    is_active       = Column(Boolean, default=True)
    last_run_at     = Column(DateTime, nullable=True)
    next_run_at     = Column(DateTime, nullable=True)
    last_status     = Column(String, nullable=True)               # success | error | running
    last_result     = Column(Text, nullable=True)                 # JSON with result details
    total_runs      = Column(Integer, default=0)
    total_entities_imported = Column(Integer, default=0)
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))

