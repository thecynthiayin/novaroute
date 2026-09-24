'use client';
import { useQuery } from '@tanstack/react-query';
import { api } from './api';

export function useInternshipStates() {
  return useQuery({
    queryKey: ['internship-states'],
    queryFn: () =>
      api<{ saved_ids: number[]; applied_ids: number[] }>('/student/internship-states'),
  });
}
