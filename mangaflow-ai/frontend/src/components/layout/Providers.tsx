"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 60 * 1000, retry: 1 } } })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "rgba(15, 15, 25, 0.95)",
            color: "#fff",
            border: "1px solid rgba(255,255,255,0.1)",
            backdropFilter: "blur(20px)",
            borderRadius: "12px",
          },
          success: { iconTheme: { primary: "#00ff88", secondary: "#000" } },
          error: { iconTheme: { primary: "#ff2d78", secondary: "#000" } },
        }}
      />
    </QueryClientProvider>
  );
}
