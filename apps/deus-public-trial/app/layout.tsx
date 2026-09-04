import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DEUS Public Trial — Compute Alliance',
  description: 'Public-safe DEUS trial with explicit compute-alliance participation, local-first processing and protected core isolation.',
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
