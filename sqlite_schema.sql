PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS presets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL CHECK (source_type IN ('builtin', 'imported_st', 'user_created')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS preset_versions (
    id TEXT PRIMARY KEY,
    preset_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    raw_source TEXT DEFAULT NULL,
    mapped_layers TEXT NOT NULL DEFAULT '{}',
    variables TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE (preset_id, version),
    FOREIGN KEY (preset_id) REFERENCES presets(id)
);

CREATE TABLE IF NOT EXISTS creation_projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT NULL,
    project_type TEXT NOT NULL CHECK (project_type IN ('original', 'adaptation')),
    ip_name TEXT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
    default_model TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS worldbooks (
    id TEXT PRIMARY KEY,
    project_id TEXT DEFAULT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('created', 'imported')),
    ui_schema TEXT NOT NULL DEFAULT '{}',
    state_schema TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES creation_projects(id)
);

CREATE TABLE IF NOT EXISTS worldbook_entries (
    id TEXT PRIMARY KEY,
    worldbook_id TEXT NOT NULL,
    title TEXT NOT NULL,
    comment TEXT DEFAULT NULL,
    keys_json TEXT NOT NULL DEFAULT '[]',
    secondary_keys_json TEXT NOT NULL DEFAULT '[]',
    content TEXT NOT NULL,
    constant INTEGER NOT NULL DEFAULT 0 CHECK (constant IN (0, 1)),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    position TEXT NOT NULL DEFAULT 'after_char' CHECK (position IN ('before_char', 'after_char', 'at_depth', 'examples')),
    insertion_order INTEGER NOT NULL DEFAULT 100,
    priority INTEGER NOT NULL DEFAULT 100,
    extensions TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (worldbook_id) REFERENCES worldbooks(id)
);

CREATE TABLE IF NOT EXISTS media_assets (
    id TEXT PRIMARY KEY,
    media_type TEXT NOT NULL CHECK (media_type IN ('image', 'document')),
    category TEXT NOT NULL CHECK (category IN ('upload', 'generated', 'reference', 'cover', 'avatar')),
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    meta TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_personas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT NULL,
    avatar_asset_id TEXT DEFAULT NULL,
    is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (avatar_asset_id) REFERENCES media_assets(id)
);

CREATE TABLE IF NOT EXISTS quick_reply_sets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    scope_type TEXT NOT NULL CHECK (scope_type IN ('global', 'card')),
    scope_id TEXT DEFAULT NULL,
    items TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS regex_scripts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    scope_type TEXT NOT NULL CHECK (scope_type IN ('global', 'card')),
    scope_id TEXT DEFAULT NULL,
    script_data TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS character_cards (
    id TEXT PRIMARY KEY,
    project_id TEXT DEFAULT NULL,
    name TEXT NOT NULL,
    name_normalized TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT NULL,
    tags_json TEXT NOT NULL DEFAULT '[]',
    cover_asset_id TEXT DEFAULT NULL,
    avatar_asset_id TEXT DEFAULT NULL,
    worldbook_id TEXT DEFAULT NULL,
    default_preset_id TEXT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    source_type TEXT NOT NULL CHECK (source_type IN ('created', 'imported_st_png', 'imported_st_json')),
    current_draft_version_id TEXT DEFAULT NULL,
    current_published_version_id TEXT DEFAULT NULL,
    latest_session_id TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    published_at TEXT DEFAULT NULL,
    FOREIGN KEY (project_id) REFERENCES creation_projects(id),
    FOREIGN KEY (cover_asset_id) REFERENCES media_assets(id),
    FOREIGN KEY (avatar_asset_id) REFERENCES media_assets(id),
    FOREIGN KEY (worldbook_id) REFERENCES worldbooks(id),
    FOREIGN KEY (default_preset_id) REFERENCES presets(id)
);

CREATE TABLE IF NOT EXISTS character_card_versions (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    version_label TEXT DEFAULT NULL,
    is_published INTEGER NOT NULL DEFAULT 0 CHECK (is_published IN (0, 1)),
    spec TEXT NOT NULL CHECK (spec IN ('izumi_v1', 'st_v3_imported')),
    source_type TEXT NOT NULL CHECK (source_type IN ('created', 'imported_st_png', 'imported_st_json')),
    base_info TEXT NOT NULL DEFAULT '{}',
    prompt_blocks TEXT NOT NULL DEFAULT '{}',
    play_config TEXT NOT NULL DEFAULT '{}',
    extension_blocks TEXT NOT NULL DEFAULT '{}',
    import_meta TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE (card_id, version),
    FOREIGN KEY (card_id) REFERENCES character_cards(id)
);

CREATE TABLE IF NOT EXISTS character_card_quick_reply_sets (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    quick_reply_set_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (card_id, quick_reply_set_id),
    FOREIGN KEY (card_id) REFERENCES character_cards(id),
    FOREIGN KEY (quick_reply_set_id) REFERENCES quick_reply_sets(id)
);

CREATE TABLE IF NOT EXISTS character_card_regex_scripts (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    regex_script_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (card_id, regex_script_id),
    FOREIGN KEY (card_id) REFERENCES character_cards(id),
    FOREIGN KEY (regex_script_id) REFERENCES regex_scripts(id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    mode TEXT NOT NULL CHECK (mode IN ('play', 'chat', 'creation')),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
    card_id TEXT DEFAULT NULL,
    card_version_id TEXT DEFAULT NULL,
    worldbook_id TEXT DEFAULT NULL,
    project_id TEXT DEFAULT NULL,
    persona_id TEXT DEFAULT NULL,
    preset_version_id TEXT DEFAULT NULL,
    origin_session_id TEXT DEFAULT NULL,
    origin_snapshot_id TEXT DEFAULT NULL,
    message_count INTEGER NOT NULL DEFAULT 0,
    last_message_id TEXT DEFAULT NULL,
    last_message_at TEXT DEFAULT NULL,
    current_state_snapshot_id TEXT DEFAULT NULL,
    model_name TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (card_id) REFERENCES character_cards(id),
    FOREIGN KEY (card_version_id) REFERENCES character_card_versions(id),
    FOREIGN KEY (worldbook_id) REFERENCES worldbooks(id),
    FOREIGN KEY (project_id) REFERENCES creation_projects(id),
    FOREIGN KEY (persona_id) REFERENCES user_personas(id),
    FOREIGN KEY (preset_version_id) REFERENCES preset_versions(id),
    FOREIGN KEY (origin_session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    sequence INTEGER NOT NULL,
    reply_to_message_id TEXT DEFAULT NULL,
    content TEXT NOT NULL,
    raw_content TEXT DEFAULT NULL,
    structured_content TEXT NOT NULL DEFAULT '[]',
    active_swipe_id TEXT DEFAULT NULL,
    token_count INTEGER DEFAULT NULL,
    is_hidden INTEGER NOT NULL DEFAULT 0 CHECK (is_hidden IN (0, 1)),
    is_locked INTEGER NOT NULL DEFAULT 0 CHECK (is_locked IN (0, 1)),
    is_edited INTEGER NOT NULL DEFAULT 0 CHECK (is_edited IN (0, 1)),
    source_type TEXT NOT NULL DEFAULT 'normal' CHECK (source_type IN ('normal', 'opening', 'regenerated', 'tool_result', 'imported')),
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT NULL,
    UNIQUE (session_id, sequence),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (reply_to_message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS conversation_snapshots (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    snapshot_type TEXT NOT NULL CHECK (snapshot_type IN ('rollback_point', 'copy_source', 'edit_cutoff')),
    message_id TEXT DEFAULT NULL,
    message_sequence INTEGER NOT NULL,
    inclusive INTEGER NOT NULL DEFAULT 1 CHECK (inclusive IN (0, 1)),
    state_snapshot_id TEXT DEFAULT NULL,
    memory_summary_ids TEXT NOT NULL DEFAULT '[]',
    label TEXT DEFAULT NULL,
    summary TEXT DEFAULT NULL,
    created_by TEXT NOT NULL DEFAULT 'system' CHECK (created_by IN ('system', 'user')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS state_snapshots (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_id TEXT DEFAULT NULL,
    variables TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS memory_summaries (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    segment_start INTEGER NOT NULL,
    segment_end INTEGER NOT NULL,
    summary TEXT NOT NULL,
    key_events TEXT NOT NULL DEFAULT '[]',
    state_snapshot_id TEXT DEFAULT NULL,
    frozen INTEGER NOT NULL DEFAULT 0 CHECK (frozen IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (state_snapshot_id) REFERENCES state_snapshots(id)
);

CREATE TABLE IF NOT EXISTS prompt_traces (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    swipe_id TEXT DEFAULT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('play', 'chat', 'creation')),
    raw_user_input TEXT DEFAULT NULL,
    normalized_input TEXT DEFAULT NULL,
    preset_layers TEXT NOT NULL DEFAULT '{}',
    injection_items TEXT NOT NULL DEFAULT '[]',
    final_messages TEXT NOT NULL DEFAULT '[]',
    token_stats TEXT NOT NULL DEFAULT '{}',
    tool_calls TEXT NOT NULL DEFAULT '[]',
    raw_response TEXT DEFAULT NULL,
    cleaned_response TEXT DEFAULT NULL,
    display_response TEXT DEFAULT NULL,
    regex_hits TEXT NOT NULL DEFAULT '[]',
    state_update TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS message_swipes (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,
    swipe_index INTEGER NOT NULL,
    generation_status TEXT NOT NULL DEFAULT 'completed' CHECK (generation_status IN ('completed', 'failed', 'aborted')),
    raw_response TEXT DEFAULT NULL,
    cleaned_response TEXT DEFAULT NULL,
    display_response TEXT DEFAULT NULL,
    provider_name TEXT DEFAULT NULL,
    model_name TEXT DEFAULT NULL,
    finish_reason TEXT DEFAULT NULL,
    token_usage TEXT NOT NULL DEFAULT '{}',
    trace_id TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (message_id, swipe_index),
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (trace_id) REFERENCES prompt_traces(id)
);

CREATE TABLE IF NOT EXISTS state_change_logs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    changes TEXT NOT NULL DEFAULT '[]',
    raw_block TEXT DEFAULT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('model', 'manual')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS long_term_memories (
    id TEXT PRIMARY KEY,
    scope_type TEXT NOT NULL CHECK (scope_type IN ('session', 'card', 'global')),
    scope_id TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('auto', 'manual')),
    importance TEXT NOT NULL DEFAULT 'medium' CHECK (importance IN ('high', 'medium', 'low')),
    source_message_id TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS tool_call_records (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments TEXT NOT NULL DEFAULT '{}',
    raw_result TEXT NOT NULL DEFAULT '{}',
    summary TEXT DEFAULT NULL,
    success INTEGER NOT NULL DEFAULT 1 CHECK (success IN (0, 1)),
    cached INTEGER NOT NULL DEFAULT 0 CHECK (cached IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS message_attachments (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,
    media_asset_id TEXT NOT NULL,
    attachment_type TEXT NOT NULL CHECK (attachment_type IN ('input_image', 'input_document', 'generated_image')),
    order_index INTEGER NOT NULL DEFAULT 0,
    caption TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (media_asset_id) REFERENCES media_assets(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_preset_versions_preset_id_version
    ON preset_versions (preset_id, version);

CREATE INDEX IF NOT EXISTS idx_presets_status
    ON presets (status);

CREATE INDEX IF NOT EXISTS idx_presets_updated_at
    ON presets (updated_at);

CREATE INDEX IF NOT EXISTS idx_creation_projects_status
    ON creation_projects (status);

CREATE INDEX IF NOT EXISTS idx_creation_projects_updated_at
    ON creation_projects (updated_at);

CREATE INDEX IF NOT EXISTS idx_worldbooks_project_id
    ON worldbooks (project_id);

CREATE INDEX IF NOT EXISTS idx_worldbooks_status
    ON worldbooks (status);

CREATE INDEX IF NOT EXISTS idx_worldbooks_updated_at
    ON worldbooks (updated_at);

CREATE INDEX IF NOT EXISTS idx_worldbook_entries_worldbook_id
    ON worldbook_entries (worldbook_id);

CREATE INDEX IF NOT EXISTS idx_worldbook_entries_enabled
    ON worldbook_entries (enabled);

CREATE INDEX IF NOT EXISTS idx_worldbook_entries_order
    ON worldbook_entries (worldbook_id, enabled, insertion_order, priority);

CREATE INDEX IF NOT EXISTS idx_media_assets_media_type
    ON media_assets (media_type);

CREATE INDEX IF NOT EXISTS idx_media_assets_category
    ON media_assets (category);

CREATE INDEX IF NOT EXISTS idx_media_assets_created_at
    ON media_assets (created_at);

CREATE INDEX IF NOT EXISTS idx_user_personas_is_default
    ON user_personas (is_default);

CREATE INDEX IF NOT EXISTS idx_quick_reply_sets_scope
    ON quick_reply_sets (scope_type, scope_id);

CREATE INDEX IF NOT EXISTS idx_regex_scripts_scope
    ON regex_scripts (scope_type, scope_id);

CREATE INDEX IF NOT EXISTS idx_character_cards_status
    ON character_cards (status);

CREATE INDEX IF NOT EXISTS idx_character_cards_project_id
    ON character_cards (project_id);

CREATE INDEX IF NOT EXISTS idx_character_cards_worldbook_id
    ON character_cards (worldbook_id);

CREATE INDEX IF NOT EXISTS idx_character_cards_updated_at
    ON character_cards (updated_at);

CREATE INDEX IF NOT EXISTS idx_character_card_versions_card_id
    ON character_card_versions (card_id);

CREATE INDEX IF NOT EXISTS idx_character_card_versions_published
    ON character_card_versions (card_id, is_published, version DESC);

CREATE INDEX IF NOT EXISTS idx_cc_quick_reply_card_id
    ON character_card_quick_reply_sets (card_id);

CREATE INDEX IF NOT EXISTS idx_cc_regex_card_id
    ON character_card_regex_scripts (card_id);

CREATE INDEX IF NOT EXISTS idx_sessions_mode_updated_at
    ON sessions (mode, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_card_id_updated_at
    ON sessions (card_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_project_id_updated_at
    ON sessions (project_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_status
    ON sessions (status);

CREATE INDEX IF NOT EXISTS idx_messages_session_sequence
    ON messages (session_id, sequence);

CREATE INDEX IF NOT EXISTS idx_messages_reply_to_message_id
    ON messages (reply_to_message_id);

CREATE INDEX IF NOT EXISTS idx_messages_created_at
    ON messages (created_at);

CREATE INDEX IF NOT EXISTS idx_message_swipes_message_id
    ON message_swipes (message_id);

CREATE INDEX IF NOT EXISTS idx_message_swipes_trace_id
    ON message_swipes (trace_id);

CREATE INDEX IF NOT EXISTS idx_conversation_snapshots_session_sequence
    ON conversation_snapshots (session_id, message_sequence DESC);

CREATE INDEX IF NOT EXISTS idx_conversation_snapshots_session_type
    ON conversation_snapshots (session_id, snapshot_type);

CREATE INDEX IF NOT EXISTS idx_state_snapshots_session_id
    ON state_snapshots (session_id);

CREATE INDEX IF NOT EXISTS idx_state_snapshots_message_id
    ON state_snapshots (message_id);

CREATE INDEX IF NOT EXISTS idx_memory_summaries_session_id
    ON memory_summaries (session_id);

CREATE INDEX IF NOT EXISTS idx_memory_summaries_segment
    ON memory_summaries (session_id, segment_start, segment_end);

CREATE INDEX IF NOT EXISTS idx_prompt_traces_session_id
    ON prompt_traces (session_id);

CREATE INDEX IF NOT EXISTS idx_prompt_traces_message_id
    ON prompt_traces (message_id);

CREATE INDEX IF NOT EXISTS idx_prompt_traces_swipe_id
    ON prompt_traces (swipe_id);

CREATE INDEX IF NOT EXISTS idx_prompt_traces_created_at
    ON prompt_traces (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_state_change_logs_session_id
    ON state_change_logs (session_id);

CREATE INDEX IF NOT EXISTS idx_state_change_logs_message_id
    ON state_change_logs (message_id);

CREATE INDEX IF NOT EXISTS idx_long_term_memories_scope
    ON long_term_memories (scope_type, scope_id);

CREATE INDEX IF NOT EXISTS idx_long_term_memories_importance
    ON long_term_memories (importance);

CREATE INDEX IF NOT EXISTS idx_tool_call_records_session_id
    ON tool_call_records (session_id);

CREATE INDEX IF NOT EXISTS idx_tool_call_records_message_id
    ON tool_call_records (message_id);

CREATE INDEX IF NOT EXISTS idx_tool_call_records_tool_name
    ON tool_call_records (tool_name);

CREATE INDEX IF NOT EXISTS idx_message_attachments_message_id
    ON message_attachments (message_id, order_index);

CREATE INDEX IF NOT EXISTS idx_message_attachments_media_asset_id
    ON message_attachments (media_asset_id);

COMMIT;

-- Notes:
-- 1. `messages.active_swipe_id` 未加外键约束，因为它与 `message_swipes.message_id`
--    形成插入阶段的循环依赖。这里建议由应用层在写入时保证一致性。
-- 2. `character_cards.current_draft_version_id` / `current_published_version_id` /
--    `latest_session_id`、`sessions.last_message_id` / `current_state_snapshot_id` /
--    `origin_snapshot_id` 也暂未加外键，原因是会产生建表与更新顺序上的循环。
--    第一阶段建议由服务层维护引用完整性，后续如迁移 PostgreSQL 可再强化约束。
