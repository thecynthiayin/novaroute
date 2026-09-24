import Link from 'next/link';
export default function NotFound() {
  return (
    <main className="landing" style={{ paddingTop: 80 }}>
      <h1>This route hasn’t been mapped.</h1>
      <p>Let’s get you back to a useful starting point.</p>
      <Link className="button" href="/">
        Back to NovaRoute
      </Link>
    </main>
  );
}
