/**
 * 他業種参考サイト 一括登録スクリプト
 * 
 * 実行方法:
 *   cd apps/web
 *   npx tsx ../../scripts/seed-cross-industry.ts
 * 
 * 前提: apps/web/.env に competitor_monitor_POSTGRES_URL が設定済み
 */

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

interface ServiceData {
  name: string;
  displayName: string;
  baseUrl: string;
  category: string;
  pages: {
    url: string;
    pageType: string;
    device: 'pc' | 'sp';
  }[];
}

const services: ServiceData[] = [
  // ============================================================
  // 1. EC系
  // ============================================================
  {
    name: 'amazon',
    displayName: 'Amazon',
    baseUrl: 'https://www.amazon.co.jp',
    category: 'other',
    pages: [
      // 検索結果一覧
      { url: 'https://www.amazon.co.jp/s?k=%E3%83%98%E3%83%83%E3%83%89%E3%83%9B%E3%83%B3', pageType: 'listing', device: 'pc' },
      { url: 'https://www.amazon.co.jp/s?k=%E3%83%98%E3%83%83%E3%83%89%E3%83%9B%E3%83%B3', pageType: 'listing', device: 'sp' },
      // 商品詳細
      { url: 'https://www.amazon.co.jp/dp/B0D1WLM4LT', pageType: 'detail', device: 'pc' },
      { url: 'https://www.amazon.co.jp/dp/B0D1WLM4LT', pageType: 'detail', device: 'sp' },
      // 購入画面（カート）
      { url: 'https://www.amazon.co.jp/gp/cart/view.html', pageType: 'form', device: 'pc' },
      { url: 'https://www.amazon.co.jp/gp/cart/view.html', pageType: 'form', device: 'sp' },
    ],
  },
  {
    name: 'mercari',
    displayName: 'メルカリ',
    baseUrl: 'https://jp.mercari.com',
    category: 'other',
    pages: [
      // 検索結果
      { url: 'https://jp.mercari.com/search?keyword=%E3%82%B9%E3%83%8B%E3%83%BC%E3%82%AB%E3%83%BC', pageType: 'listing', device: 'pc' },
      { url: 'https://jp.mercari.com/search?keyword=%E3%82%B9%E3%83%8B%E3%83%BC%E3%82%AB%E3%83%BC', pageType: 'listing', device: 'sp' },
      // 商品詳細
      { url: 'https://jp.mercari.com/item/m79108961495', pageType: 'detail', device: 'pc' },
      { url: 'https://jp.mercari.com/item/m79108961495', pageType: 'detail', device: 'sp' },
      // 購入確認画面
      { url: 'https://jp.mercari.com/transaction/confirm', pageType: 'form', device: 'pc' },
      { url: 'https://jp.mercari.com/transaction/confirm', pageType: 'form', device: 'sp' },
    ],
  },

  // ============================================================
  // 2. グルメ・予約系
  // ============================================================
  {
    name: 'tabelog',
    displayName: '食べログ',
    baseUrl: 'https://tabelog.com',
    category: 'other',
    pages: [
      // エリア検索一覧（渋谷）
      { url: 'https://tabelog.com/tokyo/A1303/A130301/rstLst/', pageType: 'listing', device: 'pc' },
      { url: 'https://tabelog.com/tokyo/A1303/A130301/rstLst/', pageType: 'listing', device: 'sp' },
      // 店舗詳細
      { url: 'https://tabelog.com/tokyo/A1301/A130101/13002566/', pageType: 'detail', device: 'pc' },
      { url: 'https://tabelog.com/tokyo/A1301/A130101/13002566/', pageType: 'detail', device: 'sp' },
      // ネット予約ページ
      { url: 'https://tabelog.com/tokyo/A1303/A130301/13283543/party/', pageType: 'visit_booking', device: 'pc' },
      { url: 'https://tabelog.com/tokyo/A1303/A130301/13283543/party/', pageType: 'visit_booking', device: 'sp' },
    ],
  },

  // ============================================================
  // 3. 旅行・宿泊予約系
  // ============================================================
  {
    name: 'booking-com',
    displayName: 'Booking.com',
    baseUrl: 'https://www.booking.com',
    category: 'other',
    pages: [
      // 検索結果（東京）
      { url: 'https://www.booking.com/searchresults.ja.html?ss=%E6%9D%B1%E4%BA%AC', pageType: 'listing', device: 'pc' },
      { url: 'https://www.booking.com/searchresults.ja.html?ss=%E6%9D%B1%E4%BA%AC', pageType: 'listing', device: 'sp' },
      // ホテル詳細
      { url: 'https://www.booking.com/hotel/jp/the-tokyo-station.ja.html', pageType: 'detail', device: 'pc' },
      { url: 'https://www.booking.com/hotel/jp/the-tokyo-station.ja.html', pageType: 'detail', device: 'sp' },
      // 予約フォーム（空室確認セクション）
      { url: 'https://www.booking.com/hotel/jp/the-tokyo-station.ja.html#availability', pageType: 'visit_booking', device: 'pc' },
      { url: 'https://www.booking.com/hotel/jp/the-tokyo-station.ja.html#availability', pageType: 'visit_booking', device: 'sp' },
    ],
  },
  {
    name: 'airbnb',
    displayName: 'Airbnb',
    baseUrl: 'https://www.airbnb.jp',
    category: 'other',
    pages: [
      // 一覧（東京）
      { url: 'https://www.airbnb.jp/tokyo-japan/stays', pageType: 'listing', device: 'pc' },
      { url: 'https://www.airbnb.jp/tokyo-japan/stays', pageType: 'listing', device: 'sp' },
      // 物件詳細
      { url: 'https://www.airbnb.jp/rooms/52813517', pageType: 'detail', device: 'pc' },
      { url: 'https://www.airbnb.jp/rooms/52813517', pageType: 'detail', device: 'sp' },
      // 予約画面
      { url: 'https://www.airbnb.jp/book/stays/52813517', pageType: 'visit_booking', device: 'pc' },
      { url: 'https://www.airbnb.jp/book/stays/52813517', pageType: 'visit_booking', device: 'sp' },
    ],
  },

  // ============================================================
  // 4. 人材・求人系
  // ============================================================
  {
    name: 'indeed',
    displayName: 'Indeed',
    baseUrl: 'https://jp.indeed.com',
    category: 'other',
    pages: [
      // 求人検索結果
      { url: 'https://jp.indeed.com/jobs?q=%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%8B%E3%82%A2&l=%E6%9D%B1%E4%BA%AC%E9%83%BD', pageType: 'listing', device: 'pc' },
      { url: 'https://jp.indeed.com/jobs?q=%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%8B%E3%82%A2&l=%E6%9D%B1%E4%BA%AC%E9%83%BD', pageType: 'listing', device: 'sp' },
      // 求人詳細（トップページで代用 - 実際の求人IDは動的）
      { url: 'https://jp.indeed.com/', pageType: 'detail', device: 'pc' },
      { url: 'https://jp.indeed.com/', pageType: 'detail', device: 'sp' },
      // 応募フォーム（トップページで代用 - 認証必要）
      { url: 'https://jp.indeed.com/career-advice/finding-a-job/guide-using-indeed.com-job-search', pageType: 'form', device: 'pc' },
      { url: 'https://jp.indeed.com/career-advice/finding-a-job/guide-using-indeed.com-job-search', pageType: 'form', device: 'sp' },
    ],
  },

  // ============================================================
  // 5. 比較・口コミ特化系
  // ============================================================
  {
    name: 'kakaku-com',
    displayName: '価格.com',
    baseUrl: 'https://kakaku.com',
    category: 'other',
    pages: [
      // カテゴリ一覧（スマートフォン）
      { url: 'https://kakaku.com/keitai/smartphone/', pageType: 'listing', device: 'pc' },
      { url: 'https://kakaku.com/keitai/smartphone/', pageType: 'listing', device: 'sp' },
      // 商品詳細・比較
      { url: 'https://kakaku.com/item/J0000043948/', pageType: 'detail', device: 'pc' },
      { url: 'https://kakaku.com/item/J0000043948/', pageType: 'detail', device: 'sp' },
      // スペック検索（条件絞り込み）
      { url: 'https://kakaku.com/specsearch/0160/', pageType: 'search', device: 'pc' },
      { url: 'https://kakaku.com/specsearch/0160/', pageType: 'search', device: 'sp' },
    ],
  },
];

async function main() {
  console.log('=== 他業種参考サイト 一括登録開始 ===\n');

  for (const svc of services) {
    // サービスの重複チェック
    const existing = await prisma.service.findFirst({
      where: { name: svc.name, deletedAt: null },
    });

    if (existing) {
      console.log(`⏭️  ${svc.displayName} (${svc.name}) は既に存在します。スキップ`);
      continue;
    }

    // サービス作成
    const service = await prisma.service.create({
      data: {
        name: svc.name,
        displayName: svc.displayName,
        baseUrl: svc.baseUrl,
        category: svc.category,
        isActive: true,
      },
    });

    console.log(`✅ ${svc.displayName} を登録 (id: ${service.id})`);

    // ページ作成
    for (const page of svc.pages) {
      await prisma.monitoredPage.create({
        data: {
          serviceId: service.id,
          url: page.url,
          pageType: page.pageType,
          device: page.device,
          isActive: true,
        },
      });
    }

    console.log(`   📄 ${svc.pages.length} ページを登録`);
  }

  console.log('\n=== 登録完了 ===');

  // サマリー表示
  const allServices = await prisma.service.findMany({
    where: { deletedAt: null, category: 'other' },
    include: { _count: { select: { pages: { where: { deletedAt: null } } } } },
    orderBy: { createdAt: 'asc' },
  });

  console.log('\n--- 他業種サービス一覧 ---');
  console.log('| サービス | ページ数 |');
  console.log('|:---------|:---------|');
  for (const s of allServices) {
    console.log(`| ${s.displayName} | ${s._count.pages} |`);
  }
}

main()
  .catch((e) => {
    console.error('エラー:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
