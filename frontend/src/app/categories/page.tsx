"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
const categoryMeta: Record<string, { label: string; icon: string; color: string }> = {
  document: { label: "Documents", icon: "📄", color: "bg-blue-500/10 text-blue-600 dark:text-blue-400" },
  prescription: { label: "Prescriptions", icon: "💊", color: "bg-green-500/10 text-green-600 dark:text-green-400" },
  receipt: { label: "Receipts", icon: "🧾", color: "bg-purple-500/10 text-purple-600 dark:text-purple-400" },
  people: { label: "People", icon: "👥", color: "bg-pink-500/10 text-pink-600 dark:text-pink-400" },
  travel: { label: "Travel", icon: "✈️", color: "bg-orange-500/10 text-orange-600 dark:text-orange-400" },
  pet: { label: "Pets", icon: "🐾", color: "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400" },
  food: { label: "Food", icon: "🍽️", color: "bg-red-500/10 text-red-600 dark:text-red-400" },
  nature: { label: "Nature", icon: "🌿", color: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" },
  other: { label: "Other", icon: "📁", color: "bg-gray-500/10 text-gray-600 dark:text-gray-400" },
};

export default function CategoriesPage() {
  const { data: categories, isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.categories.list(),
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[120px] rounded-lg" />
        ))}
      </div>
    );
  }

  if (!categories || categories.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <svg className="h-16 w-16 text-muted-foreground/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
        </svg>
        <h2 className="mt-4 text-lg font-medium">No categories yet</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload photos and they&apos;ll be automatically categorized by AI
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {categories.map((cat) => {
        const meta = categoryMeta[cat.name] || categoryMeta.other;
        return (
          <Link key={cat.name} href={`/categories/${cat.name}`}>
            <Card className="transition-shadow hover:shadow-md cursor-pointer">
              <CardContent className="p-6">
                <div className="flex items-center gap-4">
                  <div className={`flex h-14 w-14 items-center justify-center rounded-xl text-2xl ${meta.color}`}>
                    {meta.icon}
                  </div>
                  <div>
                    <h3 className="font-semibold">{meta.label}</h3>
                    <p className="text-sm text-muted-foreground">
                      {cat.count} {cat.count === 1 ? "photo" : "photos"}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        );
      })}
    </div>
  );
}
