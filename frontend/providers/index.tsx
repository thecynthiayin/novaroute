'use client';
import { useState } from 'react';
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query';
import { ThemeProvider } from 'next-themes';
import { Toaster, toast } from 'sonner';
import { api, ApiError } from '@/lib/api';
import type { User } from '@/lib/types';

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 10000,
            retry: (count, error) =>
              !(error instanceof ApiError && error.status < 500) && count < 1,
            refetchOnWindowFocus: true,
          },
        },
      }),
  );
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={client}>
        {children}
        <Toaster richColors position="bottom-right" />
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export function useAuth() {
  return useQuery({ queryKey: ['auth'], queryFn: () => api<User>('/auth/me'), retry: false });
}

export function useAction<T = unknown>(onSuccess?: (result: T) => void) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      path,
      method = 'POST',
      body,
    }: {
      path: string;
      method?: string;
      body?: unknown;
    }) => api<T>(path, method, body),
    onSuccess: async (result) => {
      await client.invalidateQueries();
      toast.success('Changes saved');
      onSuccess?.(result);
    },
    onError: (error: Error) => toast.error(error.message),
  });
}
