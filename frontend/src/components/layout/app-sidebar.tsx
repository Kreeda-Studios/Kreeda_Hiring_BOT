"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  Briefcase,
  FileText,
  FolderOpen,
  Home,
  Users,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

const mainNavItems: NavItem[] = [
  {
    title: "Home",
    href: "/",
    icon: Home,
  },
  {
    title: "Jobs",
    href: "/jobs",
    icon: Briefcase,
  },
];

const secondaryNavItems: NavItem[] = [];

interface AppSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function AppSidebar({ collapsed, onToggle }: AppSidebarProps) {
  const pathname = usePathname();
  const [theme, setTheme] = React.useState<"light" | "dark">("light");

  React.useEffect(() => {
    const root = window.document.documentElement;
    const savedTheme = localStorage.getItem("theme") as "light" | "dark" | null;
    if (savedTheme) {
      setTheme(savedTheme);
    } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      setTheme("dark");
    }

    // Listen for theme changes
    const handleThemeChange = () => {
      const newTheme = root.classList.contains("dark") ? "dark" : "light";
      setTheme(newTheme);
    };

    const observer = new MutationObserver(handleThemeChange);
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });

    return () => observer.disconnect();
  }, []);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-card transition-all duration-300",
          collapsed ? "w-[68px]" : "w-[160px]"
        )}
      >
        {/* Floating Border Edge Toggle Button */}
        <button
          onClick={onToggle}
          className="absolute -right-3 top-5 z-50 flex h-6 w-6 items-center justify-center rounded-full border bg-card text-foreground shadow-md hover:bg-accent cursor-pointer transition-transform hover:scale-110"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="h-3.5 w-3.5" />
          ) : (
            <ChevronLeft className="h-3.5 w-3.5" />
          )}
        </button>

        {/* Logo Header (100% full space) */}
        <div className="flex h-16 items-center justify-center border-b px-3">
          <Link href="/" className="flex items-center justify-center h-full w-full">
            {collapsed ? (
              <Image
                src="/r.png"
                alt="Kreeda"
                width={32}
                height={32}
                className="h-8 w-8 object-contain"
              />
            ) : (
              <Image
                src={theme === "dark" ? "/KreedaLabs_White.png" : "/KreedaLabs_Black.png"}
                alt="Kreeda Labs"
                width={140}
                height={40}
                className="h-7 w-auto object-contain max-w-[120px]"
              />
            )}
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2">
          <div className="space-y-1">
            {mainNavItems.map((item) => (
              <NavLink
                key={item.href}
                item={item}
                collapsed={collapsed}
                isActive={isActive(item.href)}
              />
            ))}
          </div>
        </nav>

        {/* Bottom Section */}
        {secondaryNavItems.length > 0 && (
          <div className="border-t p-2">
            <div className="space-y-1">
              {secondaryNavItems.map((item) => (
                <NavLink
                  key={item.href}
                  item={item}
                  collapsed={collapsed}
                  isActive={isActive(item.href)}
                />
              ))}
            </div>
          </div>
        )}
      </aside>
    </TooltipProvider>
  );
}

interface NavLinkProps {
  item: NavItem;
  collapsed: boolean;
  isActive: boolean;
}

function NavLink({ item, collapsed, isActive }: NavLinkProps) {
  const content = (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 rounded-lg px-2 py-2 text-sm font-medium transition-colors",
        isActive
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
        collapsed && "justify-center px-2"
      )}
    >
      <item.icon className="h-5 w-5 shrink-0" />
      {!collapsed && <span>{item.title}</span>}
      {!collapsed && item.badge !== undefined && (
        <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-primary/20 px-1.5 text-xs">
          {item.badge}
        </span>
      )}
    </Link>
  );

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right">{item.title}</TooltipContent>
      </Tooltip>
    );
  }

  return content;
}
