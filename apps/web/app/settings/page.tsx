import { prisma } from "@/lib/prisma";
import { Sidebar } from "@/components/sidebar";

export const dynamic = 'force-dynamic';

export default async function SettingsPage() {
  const settings = await prisma.setting.findMany();
  const settingsMap = Object.fromEntries(settings.map(s => [s.key, s.value]));

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">設定</h1>
        <div className="bg-white rounded-lg border border-gray-200 p-6 max-w-2xl">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Slack Webhook URL
              </label>
              <p className="text-sm text-gray-500 mb-2">変更検知時の通知先</p>
              <input
                type="text"
                defaultValue={settingsMap.slack_webhook_url || ""}
                placeholder="https://hooks.slack.com/services/..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                readOnly
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                スキャン頻度
              </label>
              <p className="text-sm text-gray-500">{settingsMap.scan_frequency || "daily"}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                データ保持期間
              </label>
              <p className="text-sm text-gray-500">{settingsMap.retention_days || "30"} 日</p>
            </div>
          </div>
          <p className="mt-6 text-xs text-gray-400">
            設定の変更機能は次のフェーズで実装予定です。
          </p>
        </div>
      </main>
    </div>
  );
}
