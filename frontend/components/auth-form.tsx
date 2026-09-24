'use client';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { User } from '@/lib/types';
import { Brand, Submit, ThemeSelect } from './ui';

const schema = z.object({
  email: z.email('Enter a valid email'),
  password: z.string().min(1, 'Enter your password').max(128),
  name: z.string().max(100),
  role: z.enum(['student', 'employer']),
});
type Values = z.infer<typeof schema>;
export function AuthForm({ signup = false }: { signup?: boolean }) {
  const router = useRouter(),
    client = useQueryClient(),
    search = useSearchParams();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', role: search.get('role') === 'employer' ? 'employer' : 'student' },
  });
  const mutation = useMutation({
    mutationFn: (data: Values) =>
      api<User>(
        signup ? '/auth/register' : '/auth/login',
        'POST',
        signup ? data : { email: data.email, password: data.password },
      ),
    onSuccess: (user) => {
      client.clear();
      client.setQueryData(['auth'], user);
      router.push(`/${user.role}/dashboard`);
    },
  });
  return (
    <main className="landing">
      <nav className="public-nav">
        <Brand />
        <ThemeSelect />
      </nav>
      <div className="auth-page">
        <div className="card">
          <p className="eyebrow">
            {signup ? 'Your next chapter starts here' : 'Good to see you again'}
          </p>
          <h1>{signup ? 'Create your account' : 'Welcome back.'}</h1>
          <p className="muted">
            {signup
              ? 'A clearer route from potential to opportunity.'
              : 'Sign in to pick up where you left off.'}
          </p>
          <form
            className="form-stack"
            onSubmit={handleSubmit((data) => {
              if (signup && data.password.length < 10) {
                setError('password', { message: 'Use at least 10 characters' });
                return;
              }
              if (signup && data.name.trim().length < 2) {
                setError('name', { message: 'Enter at least 2 characters' });
                return;
              }
              mutation.mutate(data);
            })}
          >
            {signup && (
              <>
                <label>
                  Full name
                  <input autoComplete="name" {...register('name')} />
                  {errors.name && <small className="error-text">{errors.name.message}</small>}
                </label>
                <fieldset>
                  <legend>I’m here as a</legend>
                  <div className="role-options">
                    <label className="role-option">
                      <input type="radio" value="student" {...register('role')} />
                      Student
                    </label>
                    <label className="role-option">
                      <input type="radio" value="employer" {...register('role')} />
                      Employer
                    </label>
                  </div>
                </fieldset>
              </>
            )}
            <label>
              Email address
              <input type="email" autoComplete="email" {...register('email')} />
              {errors.email && (
                <small className="error-text" role="alert">
                  {errors.email.message}
                </small>
              )}
            </label>
            <label>
              Password
              <input
                aria-label="Password"
                type="password"
                autoComplete={signup ? 'new-password' : 'current-password'}
                {...register('password')}
              />
              {signup && <small className="muted">At least 10 characters.</small>}
              {errors.password && (
                <small className="error-text" role="alert">
                  {errors.password.message}
                </small>
              )}
            </label>
            {mutation.error && (
              <p className="alert" role="alert">
                {mutation.error.message}
              </p>
            )}
            <Submit busy={mutation.isPending}>{signup ? 'Create account' : 'Sign in'}</Submit>
          </form>
          <hr />
          <p style={{ fontSize: 13, marginBottom: 0 }}>
            {signup ? 'Already have an account?' : 'New to NovaRoute?'}{' '}
            <Link className="text-button" href={signup ? '/login' : '/signup'}>
              {signup ? 'Sign in' : 'Create an account'}
            </Link>
          </p>
        </div>
        <p className="footer-note">
          Your profile belongs to you. Share it through your applications.
        </p>
      </div>
    </main>
  );
}
