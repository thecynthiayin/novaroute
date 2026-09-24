import type { Metadata } from 'next';
import { Providers } from '@/providers';
import './globals.css';
export const metadata: Metadata = {
  title: 'NovaRoute · Your next chapter starts here',
  description:
    'Discover technical internships that connect with your skills, coursework, and projects.',
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
