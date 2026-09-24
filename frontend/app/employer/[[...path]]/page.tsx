import { Suspense } from 'react';
import { Portal } from '@/components/portal';
export default function EmployerPage() {
  return (
    <Suspense>
      <Portal role="employer" />
    </Suspense>
  );
}
