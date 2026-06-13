"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import type { SearchResult } from "@/types";

export default function SearchPage() {
  const [query, setQuery] = useState("");

  const searchMutation = useMutation({
    mutationFn: (q: string) => api.search.query(q),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      searchMutation.mutate(query.trim());
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-bold">AI-Powered Search</h2>
        <p className="text-muted-foreground">
          Describe what you&apos;re looking for in natural language
        </p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Try "sunset at the beach" or "receipts from last month"'
            className="pl-10 h-12 text-base"
          />
        </div>
        <Button type="submit" size="lg" disabled={searchMutation.isPending}>
          {searchMutation.isPending ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
          ) : (
            "Search"
          )}
        </Button>
      </form>

      {searchMutation.isPending && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square rounded-lg" />
          ))}
        </div>
      )}

      {searchMutation.data && (
        <div>
          <div className="mb-4 flex items-center gap-2">
            <Badge variant="secondary">{searchMutation.data.length} results</Badge>
            <Badge variant="outline" className="gap-1">
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              AI-powered
            </Badge>
          </div>

          {searchMutation.data.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No results found for &ldquo;{query}&rdquo;</p>
              <p className="text-sm text-muted-foreground mt-1">Try a different description</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {searchMutation.data.map((result: SearchResult) => (
                <Link
                  key={result.image.id}
                  href={`/photos/${result.image.id}`}
                  className="group relative overflow-hidden rounded-lg border bg-card"
                >
                  <div className="aspect-square overflow-hidden bg-muted">
                    {result.image.thumbnail_url ? (
                      <img
                        src={result.image.thumbnail_url}
                        alt={result.image.filename}
                        className="h-full w-full object-cover transition-transform group-hover:scale-105"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center">
                        <svg className="h-8 w-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-3">
                    <p className="text-xs text-white/90">
                      {Math.round(result.score * 100)}% match
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {!searchMutation.data && !searchMutation.isPending && (
        <div className="text-center py-12 space-y-4">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <svg className="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Example searches:</p>
            <div className="mt-2 flex flex-wrap justify-center gap-2">
              {["dog playing in park", "mountain landscape", "birthday party", "food photography"].map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setQuery(q);
                    searchMutation.mutate(q);
                  }}
                  className="rounded-full border px-3 py-1 text-sm hover:bg-accent transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
