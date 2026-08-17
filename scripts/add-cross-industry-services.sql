-- ============================================================
-- 他業種参考サイト 一括登録SQL
-- 実行: Neon Query タブ または psql で実行
-- 日付: 2026-08-14
-- ============================================================

-- ============================================================
-- 1. EC系
-- ============================================================

-- Amazon
INSERT INTO "Service" (id, name, "displayName", "baseUrl", category, "isActive", "createdAt", "updatedAt")
VALUES (
  'svc_amazon',
  'amazon',
  'Amazon',
  'https://www.amazon.co.jp',
  'other',
  true,
  NOW(),
  NOW()
);

INSERT INTO "MonitoredPage" (id, "serviceId", url, "pageType", device, "isActive", "createdAt", "updatedAt")
VALUES
  -- 検索結果一覧（家電カテゴリ）
  ('pg_amazon_list_pc', 'svc_amazon', 'https://www.amazon.co.jp/s?k=%E3%83%98%E3%83%83%E3%83%89%E3%83%9B%E3%83%B3&ref=nb_sb_noss', 'listing', 'pc', true, NOW(), NOW()),
  ('pg_amazon_list_sp', 'svc_amazon', 'https://www.amazon.co.jp/s?k=%E3%83%98%E3%83%83%E3%83%89%E3%83%9B%E3%83%B3&ref=nb_sb_noss', 'listing', 'sp', true, NOW(), NOW()),
  -- 商品詳細（人気商品 - ソニーヘッドホン）
  ('pg_amazon_detail_pc', 'svc_amazon', 'https://www.amazon.co.jp/dp/B0D1WLM4LT', 'detail', 'pc', true, NOW(), NOW()),
  ('pg_amazon_detail_sp', 'svc_amazon', 'https://www.amazon.co.jp/dp/B0D1WLM4LT', 'detail', 'sp', true, NOW(), NOW()),
  -- 購入画面（カート）
  ('pg_amazon_form_pc', 'svc_amazon', 'https://www.amazon.co.jp/gp/cart/view.html', 'form', 'pc', true, NOW(), NOW()),
  ('pg_amazon_form_sp', 'svc_amazon', 'https://www.amazon.co.jp/gp/cart/view.html', 'form', 'sp', true, NOW(), NOW());

-- メルカリ
INSERT INTO "Service" (id, name, "displayName", "baseUrl", category, "isActive", "createdAt", "updatedAt")
VALUES (
  'svc_mercari',
  'mercari',
  'メルカリ',
  'https://jp.mercari.com',
  'other',
  true,
  NOW(),
  NOW()
);

INSERT INTO "MonitoredPage" (id, "serviceId", url, "pageType", device, "isActive", "createdAt", "updatedAt")
VALUES
  -- 検索結果一覧
  ('pg_mercari_list_pc', 'svc_mercari', 'https://jp.mercari.com/search?keyword=%E3%82%B9%E3%83%8B%E3%83%BC%E3%82%AB%E3%83%BC', 'listing', 'pc', true, NOW(), NOW()),
  ('pg_mercari_list_sp', 'svc_mercari', 'https://jp.mercari.com/search?keyword=%E3%82%B9%E3%83%8B%E3%83%BC%E3%82%AB%E3%83%BC', 'listing', 'sp', true, NOW(), NOW()),
  -- 商品詳細
  ('pg_mercari_detail_pc', 'svc_mercari', 'https://jp.mercari.com/item/m79108961495', 'detail', 'pc', true, NOW(), NOW()),
  ('pg_mercari_detail_sp', 'svc_mercari', 'https://jp.mercari.com/item/m79108961495', 'detail', 'sp', true, NOW(), NOW()),
  -- 購入画面
  ('pg_mercari_form_pc', 'svc_mercari', 'https://jp.mercari.com/transaction/confirm', 'form', 'pc', true, NOW(), NOW()),
  ('pg_mercari_form_sp', 'svc_mercari', 'https://jp.mercari.com/transaction/confirm', 'form', 'sp', true, NOW(), NOW());

-- ============================================================
-- 2. グルメ・予約系
-- ============================================================

-- 食べログ
INSERT INTO "Service" (id, name, "displayName", "baseUrl", category, "isActive", "createdAt", "updatedAt")
VALUES (
  'svc_tabelog',
  'tabelog',
  '食べログ',
  'https://tabelog.com',
  'other',
  true,
  NOW(),
  NOW()
);

INSERT INTO "MonitoredPage" (id, "serviceId", url, "pageType", device, "isActive", "createdAt", "updatedAt")
VALUES
  -- エリア検索一覧（東京・渋谷）
  ('pg_tabelog_list_pc', 'svc_tabelog', 'https://tabelog.com/tokyo/A1303/A130301/rstLst/', 'listing', 'pc', true, NOW(), NOW()),
  ('pg_tabelog_list_sp', 'svc_tabelog', 'https://tabelog.com/tokyo/A1303/A130301/rstLst/', 'listing', 'sp', true, NOW(), NOW()),
  -- 店舗詳細
  ('pg_tabelog_detail_pc', 'svc_tabelog', 'https://tabelog.com/tokyo/A1301/A130101/13002566/', 'detail', 'pc', true, NOW(), NOW()),
  ('pg_tabelog_detail_sp', 'svc_tabelog', 'https://tabelog.com/tokyo/A1301/A130101/13002566/', 'detail', 'sp', true, NOW(), NOW()),
  -- 予約ページ（ネット予約）
  ('pg_tabelog_booking_pc', 'svc_tabelog', 'https://tabelog.com/tokyo/A1303/A130301/13283543/party/', 'visit_booking', 'pc', true, NOW(), NOW()),
  ('pg_tabelog_booking_sp', 'svc_tabelog', 'https://tabelog.com/tokyo/A1303/A130301/13283543/party/', 'visit_booking', 'sp', true, NOW(), NOW());

-- ============================================================
-- 3. 旅行・宿泊予約系
-- ============================================================

-- Booking.com
INSERT INTO "Service" (id, name, "displayName", "baseUrl", category, "isActive", "createdAt", "updatedAt")
VALUES (
  'svc_booking',
  'booking-com',
  'Booking.com',
  'https://www.booking.com',
  'other',
  true,
  NOW(),
  NOW()
);

INSERT INTO "MonitoredPage" (id, "serviceId", url, "pageType", device, "isActive", "createdAt", "updatedAt")
VALUES
  -- 検索結果一覧（東京）
  ('pg_booking_list_pc', 'svc_booking', 'https://www.booking.com/searchresults.ja.html?ss=%E6%9D%B1%E4%BA%AC', 'listing', 'pc', true, NOW(), NOW()),
  ('pg_booking_list_sp', 'svc_booking', 'https://www.booking.com/searchresults.ja.html?ss=%E6%9D%B1%E4%BA%AC', 'listing', 'sp', true, NOW(), NOW()),
  -- ホテル詳細（東京の人気ホテル）
  ('pg_booking_detail_pc', 'svc_booking', 'https://www.booking.com/hotel/jp/the-tokyo-station.ja.html', 'detail', 'pc', true, NOW(), NOW()),
  ('pg_booking_detail_sp', 'svc_booking', 'https://www.booking.com/hotel/jp/the-tokyo-station.ja.html', 'detail', 'sp', true, NOW(), NOW()),
  -- 予約フォーム
  ('pg_booking_form_pc', 'svc_booking', 'https://www.booking.com/hotel/jp/the-tokyo-station.ja.html#availability', 'visit_booking', 'pc', true, NOW(), NOW()),
  ('pg_booking_form_sp', 'svc_booking', 'https://www.booking.com/hotel/jp/the-tokyo-station.ja.html#availability', 'visit_booking', 'sp', true, NOW(), NOW());

-- Airbnb
INSERT INTO "Service" (id, name, "displayName", "baseUrl", category, "isActive", "createdAt", "updatedAt")
VALUES (
  'svc_airbnb',
  'airbnb',
  'Airbnb',
  'https://www.airbnb.jp',
  'other',
  true,
  NOW(),
  NOW()
);

INSERT INTO "MonitoredPage" (id, "serviceId", url, "pageType", device, "isActive", "createdAt", "updatedAt")
VALUES
  -- 一覧ページ（東京）
  ('pg_airbnb_list_pc', 'svc_airbnb', 'https://www.airbnb.jp/tokyo-japan/stays', 'listing', 'pc', true, NOW(), NOW()),
  ('pg_airbnb_list_sp', 'svc_airbnb', 'https://www.airbnb.jp/tokyo-japan/stays', 'listing', 'sp', true, NOW(), NOW()),
  -- 物件詳細
  ('pg_airbnb_detail_pc', 'svc_airbnb', 'https://www.airbnb.jp/rooms/52813517', 'detail', 'pc', true, NOW(), NOW()),
  ('pg_airbnb_detail_sp', 'svc_airbnb', 'https://www.airbnb.jp/rooms/52813517', 'detail', 'sp', true, NOW(), NOW()),
  -- 予約画面
  ('pg_airbnb_booking_pc', 'svc_airbnb', 'https://www.airbnb.jp/book/stays/52813517', 'visit_booking', 'pc', true, NOW(), NOW()),
  ('pg_airbnb_booking_sp', 'svc_airbnb', 'https://www.airbnb.jp/book/stays/52813517', 'visit_booking', 'sp', true, NOW(), NOW());

-- ============================================================
-- 4. 人材・求人系
-- ============================================================

-- Indeed
INSERT INTO "Service" (id, name, "displayName", "baseUrl", category, "isActive", "createdAt", "updatedAt")
VALUES (
  'svc_indeed',
  'indeed',
  'Indeed',
  'https://jp.indeed.com',
  'other',
  true,
  NOW(),
  NOW()
);

INSERT INTO "MonitoredPage" (id, "serviceId", url, "pageType", device, "isActive", "createdAt", "updatedAt")
VALUES
  -- 求人検索結果
  ('pg_indeed_list_pc', 'svc_indeed', 'https://jp.indeed.com/jobs?q=%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%8B%E3%82%A2&l=%E6%9D%B1%E4%BA%AC%E9%83%BD', 'listing', 'pc', true, NOW(), NOW()),
  ('pg_indeed_list_sp', 'svc_indeed', 'https://jp.indeed.com/jobs?q=%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%8B%E3%82%A2&l=%E6%9D%B1%E4%BA%AC%E9%83%BD', 'listing', 'sp', true, NOW(), NOW()),
  -- 求人詳細
  ('pg_indeed_detail_pc', 'svc_indeed', 'https://jp.indeed.com/viewjob?jk=sample123', 'detail', 'pc', true, NOW(), NOW()),
  ('pg_indeed_detail_sp', 'svc_indeed', 'https://jp.indeed.com/viewjob?jk=sample123', 'detail', 'sp', true, NOW(), NOW()),
  -- 応募フォーム
  ('pg_indeed_form_pc', 'svc_indeed', 'https://jp.indeed.com/applystart', 'form', 'pc', true, NOW(), NOW()),
  ('pg_indeed_form_sp', 'svc_indeed', 'https://jp.indeed.com/applystart', 'form', 'sp', true, NOW(), NOW());

-- ============================================================
-- 5. 比較・口コミ特化系
-- ============================================================

-- 価格.com
INSERT INTO "Service" (id, name, "displayName", "baseUrl", category, "isActive", "createdAt", "updatedAt")
VALUES (
  'svc_kakaku',
  'kakaku-com',
  '価格.com',
  'https://kakaku.com',
  'other',
  true,
  NOW(),
  NOW()
);

INSERT INTO "MonitoredPage" (id, "serviceId", url, "pageType", device, "isActive", "createdAt", "updatedAt")
VALUES
  -- カテゴリ一覧（スマートフォン）
  ('pg_kakaku_list_pc', 'svc_kakaku', 'https://kakaku.com/keitai/smartphone/', 'listing', 'pc', true, NOW(), NOW()),
  ('pg_kakaku_list_sp', 'svc_kakaku', 'https://kakaku.com/keitai/smartphone/', 'listing', 'sp', true, NOW(), NOW()),
  -- 商品詳細・比較
  ('pg_kakaku_detail_pc', 'svc_kakaku', 'https://kakaku.com/item/J0000043948/', 'detail', 'pc', true, NOW(), NOW()),
  ('pg_kakaku_detail_sp', 'svc_kakaku', 'https://kakaku.com/item/J0000043948/', 'detail', 'sp', true, NOW(), NOW()),
  -- スペック検索（条件絞り込み）
  ('pg_kakaku_search_pc', 'svc_kakaku', 'https://kakaku.com/specsearch/0160/', 'search', 'pc', true, NOW(), NOW()),
  ('pg_kakaku_search_sp', 'svc_kakaku', 'https://kakaku.com/specsearch/0160/', 'search', 'sp', true, NOW(), NOW());

-- ============================================================
-- 確認クエリ
-- ============================================================
-- SELECT s.name, s."displayName", s.category, COUNT(p.id) as page_count
-- FROM "Service" s
-- LEFT JOIN "MonitoredPage" p ON p."serviceId" = s.id AND p."deletedAt" IS NULL
-- WHERE s."deletedAt" IS NULL AND s.category = 'other'
-- GROUP BY s.id
-- ORDER BY s."createdAt";
