CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS source_accounts (
  account_id TEXT PRIMARY KEY,
  handle TEXT NOT NULL UNIQUE,
  source_type TEXT NOT NULL,
  authority_score NUMERIC DEFAULT 70,
  reliability_score NUMERIC DEFAULT 1.0,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_posts (
  post_id TEXT PRIMARY KEY,
  author_handle TEXT NOT NULL,
  source_type TEXT NOT NULL,
  text TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TEXT NOT NULL,
  fetched_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS event_clusters (
  cluster_id TEXT PRIMARY KEY,
  main_title TEXT NOT NULL,
  event_type TEXT NOT NULL,
  hot_score NUMERIC DEFAULT 0,
  confidence_score NUMERIC DEFAULT 0,
  semantic_embedding vector(384),
  payload JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cluster_posts (
  cluster_id TEXT REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
  post_id TEXT REFERENCES raw_posts(post_id) ON DELETE CASCADE,
  PRIMARY KEY (cluster_id, post_id)
);

CREATE TABLE IF NOT EXISTS atomic_claims (
  claim_id TEXT PRIMARY KEY,
  cluster_id TEXT REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
  claim_text TEXT NOT NULL,
  entities JSONB DEFAULT '[]'::jsonb,
  verification_status TEXT DEFAULT 'unverified',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fact_checks (
  fact_check_id TEXT PRIMARY KEY,
  cluster_id TEXT REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
  verification_status TEXT NOT NULL,
  evidence_sources JSONB DEFAULT '[]'::jsonb,
  risk_note TEXT,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hot_scores (
  cluster_id TEXT PRIMARY KEY REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
  hot_score NUMERIC NOT NULL,
  score_breakdown JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS generated_contents (
  content_id TEXT PRIMARY KEY,
  cluster_id TEXT REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
  style TEXT NOT NULL,
  language TEXT NOT NULL,
  tweet_text TEXT NOT NULL,
  hashtags JSONB DEFAULT '[]'::jsonb,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS compliance_reports (
  compliance_report_id TEXT PRIMARY KEY,
  content_id TEXT REFERENCES generated_contents(content_id) ON DELETE CASCADE,
  risk_level TEXT NOT NULL,
  pass BOOLEAN NOT NULL,
  issues JSONB DEFAULT '[]'::jsonb,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS image_cards (
  id BIGSERIAL PRIMARY KEY,
  content_id TEXT REFERENCES generated_contents(content_id) ON DELETE CASCADE,
  cluster_id TEXT REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
  card_path TEXT NOT NULL,
  size TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS review_queue (
  review_id TEXT PRIMARY KEY,
  content_id TEXT REFERENCES generated_contents(content_id) ON DELETE CASCADE,
  cluster_id TEXT REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
  review_status TEXT NOT NULL,
  risk_level TEXT NOT NULL,
  payload JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS publish_records (
  publish_id TEXT PRIMARY KEY,
  content_id TEXT REFERENCES generated_contents(content_id) ON DELETE SET NULL,
  cluster_id TEXT REFERENCES event_clusters(cluster_id) ON DELETE SET NULL,
  mode TEXT NOT NULL,
  mock_post_url TEXT,
  review_status TEXT,
  payload JSONB NOT NULL,
  published_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS performance_metrics (
  id BIGSERIAL PRIMARY KEY,
  publish_id TEXT REFERENCES publish_records(publish_id) ON DELETE CASCADE,
  impressions INT DEFAULT 0,
  likes INT DEFAULT 0,
  reposts INT DEFAULT 0,
  replies INT DEFAULT 0,
  quotes INT DEFAULT 0,
  engagement_rate NUMERIC DEFAULT 0,
  payload JSONB DEFAULT '{}'::jsonb,
  captured_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS strategy_memory (
  memory_key TEXT PRIMARY KEY,
  memory_type TEXT NOT NULL,
  weight NUMERIC DEFAULT 1.0,
  payload JSONB DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS policy_rules (
  rule_id TEXT PRIMARY KEY,
  version TEXT NOT NULL,
  rule_type TEXT NOT NULL,
  rule_payload JSONB NOT NULL,
  enabled BOOLEAN DEFAULT true,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memory_change_log (
  id BIGSERIAL PRIMARY KEY,
  memory_key TEXT NOT NULL,
  old_value JSONB,
  new_value JSONB,
  reason TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS emergency_events (
  cluster_id TEXT PRIMARY KEY REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
  emergency_level TEXT NOT NULL,
  emergency_reason TEXT,
  emergency_boost NUMERIC DEFAULT 0,
  payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS ab_test_variants (
  variant_id TEXT PRIMARY KEY,
  cluster_id TEXT REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
  variant_name TEXT NOT NULL,
  payload JSONB NOT NULL,
  predicted_score NUMERIC DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform_publish_records (
  id BIGSERIAL PRIMARY KEY,
  publish_id TEXT REFERENCES publish_records(publish_id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  platform_url TEXT,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
