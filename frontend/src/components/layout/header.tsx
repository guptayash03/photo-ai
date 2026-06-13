"use client";

import { usePathname } from "next/navigation";

const titles: Record<string, string> = {
  "/": "Dashboard",
  "/photos": "Photos",
  "/search": "AI Search",
  "/faces": "People",
  "/categories": "Categories",
  "/duplicates": "Duplicates",
  "/upload": "Upload",
  "/settings": "Settings",
};

export function Header() {
  const pathname = usePathname();
  const title = titles[pathname] || titles[`/${pathname.split("/")[1]}`] || "PhotoAI";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-6">
      <h1 className="text-xl font-semibold">{title}</h1>
    </header>
  );
}
