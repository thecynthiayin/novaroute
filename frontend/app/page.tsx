import Link from 'next/link';
import { ArrowRight, BookOpen, FileCheck2, Sparkles, Waypoints } from 'lucide-react';
import { Brand, ThemeSelect } from '@/components/ui';
export default function Landing() {
  return (
    <main className="landing">
      <nav className="public-nav" aria-label="Main navigation">
        <Brand />
        <div className="actions">
          <ThemeSelect />
          <Link className="nav-login text-button" href="/login">
            Log in
          </Link>
          <Link className="button" href="/signup">
            Get started
            <ArrowRight size={15} />
          </Link>
        </div>
      </nav>
      <section className="hero">
        <div>
          <p className="eyebrow">A little direction. A world of possibility.</p>
          <h1>
            Your skills.
            <br />
            Your potential.
            <br />
            <span>Your next chapter.</span>
          </h1>
          <p className="lead">
            Find technical internships that connect with what you know—and where you want to grow.
            Let your coursework and projects tell your story.
          </p>
          <div className="actions">
            <Link className="button" href="/signup?role=student">
              Find my next step
              <ArrowRight size={17} />
            </Link>
            <Link className="button secondary" href="/signup?role=employer">
              I’m hiring
            </Link>
          </div>
          <p className="muted" style={{ fontSize: 12, marginTop: 20 }}>
            Made for computing students. Built around your experience.
          </p>
        </div>
        <div
          className="hero-art"
          aria-label="How NovaRoute connects your experience to opportunities"
        >
          <div className="hero-mini">
            <div className="actions">
              <span className="metric-icon">
                <BookOpen size={23} />
              </span>
              <span className="eyebrow" style={{ margin: 0 }}>
                Start with your story
              </span>
            </div>
            <h3 style={{ marginTop: 20 }}>More than a list of keywords.</h3>
            <p className="muted" style={{ fontSize: 13 }}>
              Bring together the things you’ve learned, the projects you’ve built, and the skills
              you want to use.
            </p>
            <div className="chips">
              <span className="chip">Your skills</span>
              <span className="chip">Your coursework</span>
              <span className="chip">Your projects</span>
            </div>
          </div>
          <div className="hero-mini">
            <div className="actions">
              <span className="metric-icon">
                <Waypoints size={23} />
              </span>
              <div>
                <h3>Find a direction that fits</h3>
                <small className="muted">Meaningful matches. Practical feedback.</small>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className="steps-section">
        <p className="eyebrow">Your route, made clearer</p>
        <h2>A thoughtful next step, from profile to application.</h2>
        <div className="grid-3" style={{ marginTop: 30 }}>
          {[
            {
              icon: FileCheck2,
              title: 'Bring your experience',
              text: 'Upload a searchable resume and review the extracted details, or build your profile by hand.',
            },
            {
              icon: Sparkles,
              title: 'Discover your fit',
              text: 'Explore internships using semantic similarity, with clear skill overlap and honest explanations.',
            },
            {
              icon: Waypoints,
              title: 'Keep moving forward',
              text: 'Follow each application, receive status updates, and turn feedback into your next learning goal.',
            },
          ].map((s, i) => (
            <article className="card" key={s.title}>
              <div className="step-number">
                0{i + 1} /{' '}
                <s.icon
                  size={18}
                  style={{ display: 'inline', verticalAlign: 'middle', marginLeft: 8 }}
                />
              </div>
              <h3>{s.title}</h3>
              <p className="muted" style={{ fontSize: 13 }}>
                {s.text}
              </p>
            </article>
          ))}
        </div>
      </section>
      <footer className="public-footer">
        <span>NovaRoute · An intelligent internship platform</span>
        <span>Built for learning. Designed for possibility.</span>
      </footer>
    </main>
  );
}
