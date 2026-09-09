"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/employees", label: "Employees" },
  { href: "/sites", label: "Sites" },
  { href: "/simulate", label: "Scenario Simulation" },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex max-w-7xl items-center gap-8 px-6 py-3">
        <div>
          <p className="text-sm font-semibold tracking-tight text-foreground">Kinvera</p>
          <p className="text-[11px] text-muted">Ironbridge Field Operations</p>
        </div>
        <nav className="flex gap-1">
          {LINKS.map((link) => {
            const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  active ? "bg-accent text-accent-foreground" : "text-muted hover:bg-gray-100 hover:text-foreground"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
