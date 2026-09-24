"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  MessageSquare,
  CloudSun,
  FileText,
  ClipboardList,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  {
    name: "Dashboard",
    href: "/",
    icon: Home,
  },
  {
    name: "Ask GeoVault",
    href: "/ask",
    icon: MessageSquare,
  },
  {
    name: "Topics & Word Cloud",
    href: "/topics",
    icon: CloudSun,
  },
  {
    name: "Report Generator",
    href: "/reports",
    icon: FileText,
  },
  {
    name: "Logs",
    href: "/logs",
    icon: ClipboardList,
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 lg:w-72 bg-[#1E222A] text-slate-200 flex flex-col shrink-0 border-r border-[#2C323E] z-30 select-none h-full">
      {/* Primary Navigation List */}
      <nav className="flex-1 px-3.5 py-5 space-y-2 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3.5 px-4 py-2.5 rounded-xl text-[15px] transition-all duration-150 ${
                isActive
                  ? "bg-[#2F3644] text-white font-bold shadow-sm"
                  : "text-slate-300 hover:text-white hover:bg-[#282E3A] font-semibold"
              }`}
            >
              <Icon
                className={`w-5 h-5 shrink-0 transition-colors ${
                  isActive ? "text-white stroke-[2.2]" : "text-slate-400"
                }`}
              />
              <span className="leading-none">{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
