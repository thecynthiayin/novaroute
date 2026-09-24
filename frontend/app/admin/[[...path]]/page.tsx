import { Suspense } from 'react';
import { Portal } from '@/components/portal';

export default function Page() {
  return (
    <Suspense>
      <Portal role="admin" />
    </Suspense>
  );
}