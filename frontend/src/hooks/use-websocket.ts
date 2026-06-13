"use client";

import { useEffect, useState } from "react";
import { wsClient } from "@/lib/websocket";
import type { WebSocketMessage } from "@/types";

export function useWebSocket() {
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  useEffect(() => {
    const unsubscribe = wsClient.subscribe((msg) => {
      setLastMessage(msg);
    });
    return unsubscribe;
  }, []);

  return { lastMessage };
}

export function useJobProgress(jobId: string | null) {
  const [progress, setProgress] = useState<{ processed: number; total: number } | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (!jobId) return;

    const unsubscribe = wsClient.subscribe((msg) => {
      if (msg.job_id !== jobId) return;
      if (msg.type === "progress") {
        setProgress({ processed: msg.data.processed, total: msg.data.total });
      } else if (msg.type === "complete") {
        setIsComplete(true);
      }
    });

    return unsubscribe;
  }, [jobId]);

  return { progress, isComplete };
}
