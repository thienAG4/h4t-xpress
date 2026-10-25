// App - providers, session restore on start-up, router and toasts

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { RouterProvider } from "react-router/dom";
import { Toaster } from "@/components/ui";
import { refreshSession } from "@/lib/http";
import { router } from "./router";

export function App() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: 1 },
        },
      }),
  );

  // The refresh cookie survives reloads; exchange it for an access token once on start-up.
  useEffect(() => {
    void refreshSession();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster />
    </QueryClientProvider>
  );
}
