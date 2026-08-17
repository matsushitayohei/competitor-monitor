-- Register HOME'S pages for UIUX structure monitoring
-- Run after migrate_page_structure.sql
-- Date: 2026-08-14

-- 注意: 
-- 物件詳細URLは掲載切れになる可能性があります。
-- 掲載切れになったら一覧ページから新しい物件URLを取得して更新してください。
-- UPDATE "OwnPage" SET url = '新URL', "updatedAt" = NOW() WHERE id = '対象ID';

-- === 賃貸 SP ===

-- 物件詳細 SP（問い合わせフォームが埋め込まれているため、form分析もここで実施）
INSERT INTO "OwnPage" (id, name, "pageType", url, device, category) VALUES
  (gen_random_uuid()::text, 'HOME''S 賃貸 物件詳細 SP', 'detail', 
   'https://www.homes.co.jp/chintai/room/c427ff08785ddef1731c72e4befb90a272f3eb9b/', 'sp', 'chintai');

-- 一覧 SP（東京・文京区 — 安定したURL）
INSERT INTO "OwnPage" (id, name, "pageType", url, device, category) VALUES
  (gen_random_uuid()::text, 'HOME''S 賃貸 一覧 SP', 'list', 
   'https://www.homes.co.jp/chintai/tokyo/bunkyo-city/list/', 'sp', 'chintai');

-- === 賃貸 PC ===

-- 物件詳細 PC（同じ物件、PCビュー）
INSERT INTO "OwnPage" (id, name, "pageType", url, device, category) VALUES
  (gen_random_uuid()::text, 'HOME''S 賃貸 物件詳細 PC', 'detail', 
   'https://www.homes.co.jp/chintai/room/c427ff08785ddef1731c72e4befb90a272f3eb9b/', 'pc', 'chintai');

-- 一覧 PC
INSERT INTO "OwnPage" (id, name, "pageType", url, device, category) VALUES
  (gen_random_uuid()::text, 'HOME''S 賃貸 一覧 PC', 'list', 
   'https://www.homes.co.jp/chintai/tokyo/bunkyo-city/list/', 'pc', 'chintai');

-- === トップ ===

-- 賃貸トップ SP
INSERT INTO "OwnPage" (id, name, "pageType", url, device, category) VALUES
  (gen_random_uuid()::text, 'HOME''S 賃貸 トップ SP', 'top', 
   'https://www.homes.co.jp/chintai/', 'sp', 'chintai');

-- 賃貸トップ PC
INSERT INTO "OwnPage" (id, name, "pageType", url, device, category) VALUES
  (gen_random_uuid()::text, 'HOME''S 賃貸 トップ PC', 'top', 
   'https://www.homes.co.jp/chintai/', 'pc', 'chintai');

-- =============================
-- 検証クエリ
-- =============================
-- SELECT id, name, "pageType", device, url FROM "OwnPage" WHERE "deletedAt" IS NULL ORDER BY category, "pageType", device;
