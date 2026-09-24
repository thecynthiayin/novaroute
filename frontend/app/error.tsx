'use client';
import { Failure } from '@/components/ui';
export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <main className="landing" style={{ paddingTop: 70 }}>
      <Failure error={error} retry={reset} />
    </main>
  );
}
