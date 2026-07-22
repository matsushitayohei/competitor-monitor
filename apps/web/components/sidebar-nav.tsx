"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = {
  href: string;
  label: string;
  icon: string;
};

type NavSection = {
  id: string;
  heading: string;
  items: NavItem[];
};

const sections: NavSection[] = [
  {
    id: "uiux",
    heading: "UIUX",
    items: [
      { href: "/dashboard", label: "ダッシュボード", icon: "📊" },
      { href: "/sites", label: "対象サイト", icon: "🌐" },
      { href: "/changes", label: "変更履歴", icon: "🔄" },
      { href: "/advice", label: "AIアドバイス", icon: "💡" },
    ],
  },
  {
    id: "press",
    heading: "PRESS",
    items: [
      { href: "/press", label: "ソース管理", icon: "📰" },
      { href: "/press/articles", label: "記事履歴", icon: "📄" },
    ],
  },
];

const standaloneItems: NavItem[] = [
  { href: "/settings", label: "設定", icon: "⚙️" },
];

type SidebarNavItemProps = {
  item: NavItem;
  pathname: string;
};

export function SidebarNavItem({ item, pathname }: SidebarNavItemProps) {
  const isActive = pathname === item.href;
  return (
    <Link
      href={item.href}
      aria-current={isActive ? "page" : undefined}
      className={[
        "flex items-center gap-3 px-3 py-2 text-sm rounded-lg transition-colors",
        isActive
          ? "bg-gray-100 text-gray-900 font-semibold"
          : "text-gray-700 hover:bg-gray-100",
      ].join(" ")}
    >
      <span>{item.icon}</span>
      <span>{item.label}</span>
    </Link>
  );
}

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <nav className="flex-1">
      {sections.map((section, idx) => (
        <section
          key={section.id}
          aria-labelledby={`${section.id}-heading`}
          className={idx > 0 ? "mt-6" : ""}
        >
          <h2
            id={`${section.id}-heading`}
            className="px-3 mb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider"
          >
            {section.heading}
          </h2>
          <div className="space-y-1">
            {section.items.map((item) => (
              <SidebarNavItem key={item.href} item={item} pathname={pathname} />
            ))}
          </div>
        </section>
      ))}

      {/* Standalone items */}
      <div className="mt-6 space-y-1">
        {standaloneItems.map((item) => (
          <SidebarNavItem key={item.href} item={item} pathname={pathname} />
        ))}
      </div>
    </nav>
  );
}
