'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export default function Providers({ children }: { children: React.ReactNode }) {
    // Create QueryClient inside state so it's stable across renders
    // but unique per SSR request (avoids sharing cache between users).
    const [queryClient] = useState(
        () =>
            new QueryClient({
                defaultOptions: {
                    queries: {
                        staleTime: 30_000,        // Data is fresh for 30 s — avoids needless refetches on tab switches
                        refetchOnWindowFocus: true, // Auto-refresh when user alt-tabs back
                    },
                },
            }),
    );

    return (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );
}
