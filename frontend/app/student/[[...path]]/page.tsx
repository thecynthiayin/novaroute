import { Suspense } from 'react';
import { Portal } from '@/components/portal';
export default function StudentPage() {
  return (
    <Suspense>
      <Portal role="student" />
    </Suspense>
  );
}
