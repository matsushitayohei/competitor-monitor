import { signOut } from "@/lib/auth";
import { SidebarNav } from "./sidebar-nav";

export function Sidebar() {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen p-4 flex flex-col">
      <div className="mb-8">
        <h1 className="text-lg font-bold text-gray-900">Competitor Monitor</h1>
        <p className="text-xs text-gray-500">競合UIUX監視</p>
      </div>
      <SidebarNav />
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
