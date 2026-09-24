'use client';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileUp } from 'lucide-react';
import { api, date } from '@/lib/api';
import type { Company, Profile, Resume } from '@/lib/types';
import { useAction } from '@/providers';
import { Badge, Confirm, Failure, Form, Heading, Loading, Projects, Submit, Tags } from './ui';

export function StudentProfilePage() {
  const query = useQuery({
    queryKey: ['profile'],
    queryFn: () => api<Profile>('/student/profile'),
  });
  return (
    <>
      <Heading eyebrow="A story only you can tell" title="Your experience, in focus">
        Build a profile around what you’ve learned and what you’ve made.
      </Heading>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Failure error={query.error} retry={() => query.refetch()} />
      ) : (
        <div className="split">
          <ProfileEditor key={query.data.version} profile={query.data} />
          <ResumeManager profile={query.data} />
        </div>
      )}
    </>
  );
}

function ProfileEditor({ profile }: { profile: Profile }) {
  const [skills, setSkills] = useState(profile.extracted_skills),
    [coursework, setCoursework] = useState(profile.coursework),
    [projects, setProjects] = useState(profile.projects),
    action = useAction();
  return (
    <section className="card">
      <h2>Make it yours</h2>
      <p className="muted" style={{ fontSize: 13 }}>
        You can edit everything here, with or without a resume. Press Enter or Add to save each
        skill entry into the form.
      </p>
      <Form
        initial={{
          degree: profile.degree,
          location: profile.location,
          work_mode: profile.preferences.work_mode || '',
          interests: profile.preferences.interests || '',
        }}
        fields={[
          { name: 'degree', label: 'Degree / major', maxLength: 200 },
          { name: 'location', label: 'Preferred location', maxLength: 200 },
          {
            name: 'work_mode',
            label: 'Preferred work mode',
            options: ['', 'remote', 'hybrid', 'onsite'],
          },
          {
            name: 'interests',
            label: 'Interests and preferences',
            type: 'textarea',
            maxLength: 500,
          },
        ]}
        onSubmit={async (values) => {
          await action.mutateAsync({
            path: '/student/profile',
            method: 'PATCH',
            body: {
              degree: values.degree,
              location: values.location,
              preferences: { work_mode: values.work_mode, interests: values.interests },
              extracted_skills: skills,
              coursework,
              projects,
              version: profile.version,
            },
          });
        }}
        busy={action.isPending}
      >
        <Tags label="Skills" values={skills} onChange={setSkills} />
        <Tags label="Coursework" values={coursework} onChange={setCoursework} />
        <Projects values={projects} onChange={setProjects} />
      </Form>
      <hr />
      <Confirm
        title="Clear resume-derived entries?"
        description="Remove entries originally added by resume confirmation and clear raw resume text. Entries that existed manually before confirmation remain. Review the remaining profile afterwards."
        trigger={<button className="text-button danger-text">Clear resume-derived entries</button>}
        onConfirm={() =>
          action.mutateAsync({
            path: '/student/profile/clear-resume',
            body: { version: profile.version },
          })
        }
        busy={action.isPending}
      />
    </section>
  );
}

function ResumeManager({ profile }: { profile: Profile }) {
  const query = useQuery({
      queryKey: ['resumes'],
      queryFn: () => api<Resume[]>('/student/resumes'),
    }),
    action = useAction();
  const [file, setFile] = useState<File | null>(null),
    [review, setReview] = useState<number | null>(null);
  const current = query.data?.find((r) => r.id === review);
  return (
    <aside className="stack">
      <section className="card">
        <div className="actions" style={{ marginBottom: 16 }}>
          <span className="metric-icon">
            <FileUp size={22} />
          </span>
          <h2 style={{ margin: 0 }}>Start with your resume</h2>
        </div>
        <p className="muted" style={{ fontSize: 13 }}>
          Less typing, more possibility. Upload, review the draft, then confirm the details you want
          to add.
        </p>
        <form
          className="upload-zone"
          onSubmit={async (e) => {
            e.preventDefault();
            if (!file) return;
            const body = new FormData();
            body.append('file', file);
            try {
              const result = (await action.mutateAsync({ path: '/upload-resume', body })) as Resume;
              setReview(result.id);
            } catch {
              /* Keep the selected file and show the mutation's error toast. */
            }
          }}
        >
          <label>
            Searchable PDF resume
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required
            />
          </label>
          <p>
            Up to 5 MB and 10 pages by default. Scanned images are not supported. In live mode,
            extracted text is processed by the configured OpenRouter AI provider after contact
            redaction. Review before confirming; your current profile is preserved on failure.
          </p>
          <Submit busy={action.isPending}>Upload & extract</Submit>
          {action.isPending && (
            <p role="status">Reading your PDF and extracting a draft. This can take a minute.</p>
          )}
        </form>
      </section>
      {query.error && <Failure error={query.error} />}
      <section className="card">
        <h2>Your resumes</h2>
        {query.data?.length === 0 && (
          <p className="muted" style={{ fontSize: 13 }}>
            No resume uploaded yet. Manual profile entry is always available.
          </p>
        )}
        {query.data?.map((item) => (
          <div className="resume-row" key={item.id}>
            <div className="status-row">
              <strong style={{ fontSize: 13, overflowWrap: 'anywhere' }}>{item.filename}</strong>
              <Badge>{item.parse_state}</Badge>
            </div>
            <small className="muted">Uploaded {date(item.created_at)}</small>
            {item.failure && (
              <p className="alert" style={{ marginTop: 10 }}>
                {item.failure}
              </p>
            )}
            <div className="actions" style={{ marginTop: 10 }}>
              {item.parse_state === 'draft' && (
                <button className="text-button" onClick={() => setReview(item.id)}>
                  Review extraction
                </button>
              )}
              <a className="text-button" href={`/api/student/resumes/${item.id}/download`} download>
                Download
              </a>
              <Confirm
                title="Delete private resume?"
                description="Delete the private PDF, raw text, and its extraction. Already confirmed profile entries remain. Use Clear resume-derived entries to remove those too."
                trigger={<button className="text-button danger-text">Delete</button>}
                onConfirm={() =>
                  action.mutateAsync({ path: `/student/resumes/${item.id}`, method: 'DELETE' })
                }
                busy={action.isPending}
              />
            </div>
          </div>
        ))}
      </section>
      {current?.parse_state === 'draft' && (
        <Draft key={current.id} resume={current} profile={profile} onDone={() => setReview(null)} />
      )}
    </aside>
  );
}

function Draft({
  resume,
  profile,
  onDone,
}: {
  resume: Resume;
  profile: Profile;
  onDone: () => void;
}) {
  const [skills, setSkills] = useState(resume.extracted.skills),
    [coursework, setCoursework] = useState(resume.extracted.coursework),
    [projects, setProjects] = useState(resume.extracted.projects),
    [education, setEducation] = useState(resume.extracted.education),
    action = useAction(onDone);
  const stale = profile.version !== resume.profile_version;
  return (
    <section className="card">
      <h2>Review your extraction</h2>
      <p className="muted" style={{ fontSize: 13 }}>
        Correct any missing or inaccurate facts. Confirmation merges these entries into your
        profile. Reviewed education fills an empty degree field; an existing degree is preserved.
      </p>
      {stale && (
        <p className="alert">
          Your profile changed after this upload. Copy useful entries manually or upload again; this
          draft cannot overwrite newer edits.
        </p>
      )}
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault();
          action.mutate({
            path: `/student/resumes/${resume.id}/confirm`,
            body: { skills, coursework, projects, education, version: resume.profile_version },
          });
        }}
      >
        <Tags label="Extracted skills" values={skills} onChange={setSkills} />
        <Tags label="Extracted coursework" values={coursework} onChange={setCoursework} />
        <Projects values={projects} onChange={setProjects} />
        <Tags label="Education" values={education} onChange={setEducation} />
        <Submit busy={action.isPending || stale}>Confirm profile details</Submit>
      </form>
    </section>
  );
}

export function EmployerProfilePage() {
  const query = useQuery({
      queryKey: ['company'],
      queryFn: () => api<Company>('/employer/profile'),
    }),
    action = useAction();
  return (
    <>
      <Heading eyebrow="Introduce your team" title="Company profile">
        Give students a clear picture of where they could grow.
      </Heading>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Failure error={query.error} />
      ) : (
        <section className="card narrow">
          <Form
            key={JSON.stringify(query.data)}
            fields={[
              { name: 'company_name', label: 'Company name', required: true, maxLength: 150 },
              {
                name: 'website',
                label: 'Company website',
                type: 'url',
                hint: 'Use a full https:// URL, or leave blank.',
              },
              { name: 'industry', label: 'Industry', maxLength: 150 },
              { name: 'location', label: 'Company location', maxLength: 200 },
              {
                name: 'description',
                label: 'About your company',
                type: 'textarea',
                maxLength: 5000,
              },
            ]}
            initial={{
              company_name: query.data.company_name,
              website: query.data.website,
              industry: query.data.industry,
              location: query.data.location,
              description: query.data.description,
            }}
            onSubmit={async (values) => {
              await action.mutateAsync({
                path: '/employer/profile',
                method: 'PATCH',
                body: Object.fromEntries(
                  ['company_name', 'website', 'industry', 'location', 'description'].map((k) => [
                    k,
                    values[k] || '',
                  ]),
                ),
              });
            }}
            busy={action.isPending}
          />
        </section>
      )}
    </>
  );
}
