'use client';
import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useTheme } from 'next-themes';
import { ArrowRight, Check, LoaderCircle, Plus, X } from 'lucide-react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { human } from '@/lib/api';
import type { Project } from '@/lib/types';

export function ThemeSelect() {
  const { theme, setTheme } = useTheme();
  return (
    <select
      aria-label="Color theme"
      value={theme || 'system'}
      onChange={(e) => setTheme(e.target.value)}
      suppressHydrationWarning
      className="theme-select"
    >
      <option value="system">System theme</option>
      <option value="light">Light theme</option>
      <option value="dark">Dark theme</option>
    </select>
  );
}
export function Brand() {
  return (
    <Link href="/" className="brand">
      <span className="brand-symbol">
        N<span>↗</span>
      </span>
      NovaRoute<span className="brand-dot">.</span>
    </Link>
  );
}
export function Badge({ children }: { children: React.ReactNode }) {
  return <span className="badge">{typeof children === 'string' ? human(children) : children}</span>;
}
export function Loading() {
  return (
    <div aria-label="Loading" aria-busy="true" className="skeletons">
      {[1, 2, 3].map((x) => (
        <div className="skeleton" key={x} />
      ))}
    </div>
  );
}
export function Failure({ error, retry }: { error: Error; retry?: () => void }) {
  return (
    <div className="alert" role="alert">
      <strong>We couldn’t load this yet</strong>
      <p>{error.message}</p>
      {retry && (
        <button className="button secondary" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
export function Empty({
  title,
  children,
  href,
  action,
}: {
  title: string;
  children?: React.ReactNode;
  href?: string;
  action?: string;
}) {
  return (
    <div className="empty">
      <span className="empty-mark">✧</span>
      <h3>{title}</h3>
      <p>{children}</p>
      {href && (
        <Link className="button secondary" href={href}>
          {action || 'Explore internships'}
          <ArrowRight size={16} />
        </Link>
      )}
    </div>
  );
}
export function Heading({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow?: string;
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {children && <p className="muted">{children}</p>}
      </div>
      {action}
    </div>
  );
}
export function Submit({
  busy,
  children = 'Save changes',
}: {
  busy?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <button type="submit" className="button" disabled={busy}>
      {busy ? <LoaderCircle className="spin" size={17} /> : <Check size={17} />}{' '}
      {busy ? 'Saving…' : children}
    </button>
  );
}
export function Confirm({
  title,
  description,
  trigger,
  onConfirm,
  busy,
}: {
  title: string;
  description: string;
  trigger: React.ReactNode;
  onConfirm: () => Promise<unknown>;
  busy?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="modal">
          <Dialog.Title>{title}</Dialog.Title>
          <Dialog.Description>{description}</Dialog.Description>
          <div className="actions">
            <Dialog.Close className="button secondary">Cancel</Dialog.Close>
            <button
              className="button danger"
              disabled={busy}
              onClick={async () => {
                try {
                  await onConfirm();
                  setOpen(false);
                } catch {
                  /* Mutation renders its server error as a toast. */
                }
              }}
            >
              Confirm
            </button>
          </div>
          <Dialog.Close className="modal-close" aria-label="Close dialog">
            <X size={20} />
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export function Tags({
  label,
  values,
  onChange,
}: {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
}) {
  const [value, setValue] = useState('');
  const add = () => {
    const additions = value
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean);
    onChange([...new Set([...values, ...additions])].slice(0, 60));
    setValue('');
  };
  return (
    <fieldset className="tags-editor">
      <legend>{label}</legend>
      <div className="chips">
        {values.map((x, i) => (
          <span className="chip" key={`${x}-${i}`}>
            {x}
            <button
              type="button"
              aria-label={`Remove ${x}`}
              onClick={() => onChange(values.filter((_, n) => n !== i))}
            >
              <X size={13} />
            </button>
          </span>
        ))}
      </div>
      <div className="inline-field">
        <input
          aria-label={`Add ${label.toLowerCase()}`}
          placeholder="Type an entry, then press Enter"
          value={value}
          maxLength={150}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              add();
            }
          }}
        />
        <button className="button secondary" type="button" onClick={add}>
          <Plus size={16} />
          Add
        </button>
      </div>
    </fieldset>
  );
}
export function Projects({
  values,
  onChange,
}: {
  values: Project[];
  onChange: (values: Project[]) => void;
}) {
  const change = (i: number, part: Partial<Project>) =>
    onChange(values.map((p, n) => (n === i ? { ...p, ...part } : p)));
  return (
    <fieldset>
      <legend>Projects</legend>
      {values.map((p, i) => (
        <div className="project-editor" key={i}>
          <label>
            Project title
            <input
              aria-label={`Project ${i + 1} title`}
              value={p.title}
              maxLength={200}
              onChange={(e) => change(i, { title: e.target.value })}
            />
          </label>
          <label>
            Description
            <textarea
              aria-label={`Project ${i + 1} description`}
              value={p.description}
              maxLength={1500}
              onChange={(e) => change(i, { description: e.target.value })}
            />
          </label>
          <Tags
            label={`Project ${i + 1} technologies`}
            values={p.technologies}
            onChange={(technologies) => change(i, { technologies })}
          />
          <button
            type="button"
            className="text-button danger-text"
            onClick={() => onChange(values.filter((_, n) => n !== i))}
          >
            Remove project
          </button>
        </div>
      ))}
      <button
        type="button"
        className="button secondary"
        onClick={() => onChange([...values, { title: '', description: '', technologies: [] }])}
        disabled={values.length >= 20}
      >
        <Plus size={16} />
        Add project
      </button>
    </fieldset>
  );
}
export type Field = {
  name: string;
  label: string;
  type?: string;
  required?: boolean;
  options?: string[];
  hint?: string;
  maxLength?: number;
};
export function Form({
  fields,
  initial,
  onSubmit,
  busy,
  children,
  submitLabel,
}: {
  fields: Field[];
  initial?: Record<string, string>;
  onSubmit: (values: Record<string, string>) => void | Promise<void>;
  busy?: boolean;
  children?: React.ReactNode;
  submitLabel?: string;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Record<string, string>>({ defaultValues: initial });
  return (
    <form
      className="form-stack"
      onSubmit={handleSubmit(async (values) => {
        try {
          await onSubmit(values);
        } catch {
          /* useAction shows the sanitized error; preserve the form. */
        }
      })}
    >
      {fields.map((f) => (
        <label key={f.name}>
          {f.label}
          {f.type === 'textarea' ? (
            <textarea
              aria-label={f.label}
              {...register(f.name, {
                required: f.required ? 'This field is required' : false,
                maxLength: f.maxLength || 12000,
              })}
            />
          ) : f.options ? (
            <select aria-label={f.label} {...register(f.name)}>
              {f.options.map((o) => (
                <option value={o} key={o}>
                  {o ? human(o) : 'No preference'}
                </option>
              ))}
            </select>
          ) : (
            <input
              aria-label={f.label}
              type={f.type || 'text'}
              step={f.type === 'number' ? '0.01' : undefined}
              min={f.type === 'number' ? '0' : undefined}
              maxLength={f.maxLength || 500}
              {...register(f.name, { required: f.required ? 'This field is required' : false })}
            />
          )}
          {f.hint && <small className="muted">{f.hint}</small>}
          {errors[f.name] && (
            <small role="alert" className="error-text">
              {errors[f.name]?.message}
            </small>
          )}
        </label>
      ))}
      {children}
      <Submit busy={busy}>{submitLabel}</Submit>
    </form>
  );
}
export function Pagination({
  page,
  total,
  size,
  setPage,
}: {
  page: number;
  total: number;
  size: number;
  setPage: (n: number) => void;
}) {
  return (
    <div className="pagination">
      <span>
        {total} results · Page {page} of {Math.max(1, Math.ceil(total / size))}
      </span>
      <div className="actions">
        <button
          className="button secondary"
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
        >
          Previous
        </button>
        <button
          className="button secondary"
          disabled={page * size >= total}
          onClick={() => setPage(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
