-- Initial schema for Competitor Monitor

-- Services table (competitor sites)
CREATE TABLE services (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  display_name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

-- Monitored pages
CREATE TABLE monitored_pages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  service_id UUID REFERENCES services(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  page_type TEXT NOT NULL CHECK (page_type IN ('listing', 'detail')),
  device TEXT NOT NULL DEFAULT 'pc' CHECK (device IN ('pc', 'sp')),
  is_active BOOLEAN DEFAULT true,
  last_scanned_at TIMESTAMPTZ,
  last_status INTEGER,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

-- Snapshots (screenshots + DOM)
CREATE TABLE snapshots (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  page_id UUID REFERENCES monitored_pages(id) ON DELETE CASCADE,
  screenshot_path TEXT,
  dom_hash TEXT,
  dom_structure TEXT,
  captured_at TIMESTAMPTZ DEFAULT now()
);

-- Detected changes
CREATE TABLE changes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  page_id UUID REFERENCES monitored_pages(id) ON DELETE CASCADE,
  service_name TEXT NOT NULL,
  page_type TEXT NOT NULL,
  category TEXT CHECK (category IN ('CRO', 'AD_PRODUCT', 'SEO', 'AI', 'OTHER')),
  summary TEXT,
  diff_text TEXT,
  before_screenshot_path TEXT,
  after_screenshot_path TEXT,
  visual_diff_path TEXT,
  detected_at TIMESTAMPTZ DEFAULT now(),
  is_reviewed BOOLEAN DEFAULT false
);

-- AI advice
CREATE TABLE advice (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  change_id UUID REFERENCES changes(id) ON DELETE CASCADE,
  summary TEXT,
  intent TEXT,
  proposal TEXT,
  priority TEXT CHECK (priority IN ('high', 'medium', 'low')),
  expected_effect TEXT,
  risks TEXT,
  raw_response JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- App settings
CREATE TABLE settings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  value TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Insert initial services
INSERT INTO services (name, display_name, base_url) VALUES
  ('suumo', 'SUUMO', 'https://suumo.jp'),
  ('athome', 'athome', 'https://www.athome.co.jp'),
  ('canary', 'カナリー', 'https://www.canary-app.jp');

-- Insert default settings
INSERT INTO settings (key, value) VALUES
  ('slack_webhook_url', ''),
  ('scan_frequency', 'daily'),
  ('retention_days', '30');

-- Enable RLS
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE monitored_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE changes ENABLE ROW LEVEL SECURITY;
ALTER TABLE advice ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- RLS policies (allow authenticated users)
CREATE POLICY "Allow authenticated read" ON services FOR SELECT TO authenticated USING (true);
CREATE POLICY "Allow authenticated read" ON monitored_pages FOR SELECT TO authenticated USING (true);
CREATE POLICY "Allow authenticated read" ON snapshots FOR SELECT TO authenticated USING (true);
CREATE POLICY "Allow authenticated read" ON changes FOR SELECT TO authenticated USING (true);
CREATE POLICY "Allow authenticated read" ON advice FOR SELECT TO authenticated USING (true);
CREATE POLICY "Allow authenticated read" ON settings FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated write" ON services FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow authenticated write" ON monitored_pages FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow authenticated write" ON settings FOR ALL TO authenticated USING (true);
