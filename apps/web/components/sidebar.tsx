import Link from "next/link";
import { signOut } from "@/lib/auth";

const navItems = [
  { href: "/dashboard", label: "ダッシュボード", icon: "📊" },
  { href: "/sites", label: "対象サイト", icon: "🌐" },
  { href: "/changes", label: "変更履歴", icon: "🔄" },
  { href: "/advice", label: "AIアドバイス", icon: "💡" },
  { href: "/settings", label: "設定", icon: "⚙️" },
];

export function Sidebar() {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen p-4 flex flex-col">
      <div className="mb-8">
        <h1 className="text-lg font-bold text-gray-900">Competitor Monitor</h1>
        <p className="text-xs text-gray-500">競合UIUX監視</p>
      </div>
      <nav className="flex-1 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center gap-3 px-3 py-2 text-sm text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
      <form
        action={async () => {
          "use server";
          await signOut({ redirectTo: "/login" });
        }}
      >
        <button
          type="submit"
          className="w-full text-left px-3 py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          ログアウト
        </button>
      </form>
    </aside>
  );
}
