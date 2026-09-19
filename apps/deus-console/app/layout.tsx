import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DEUS Work Interface',
  description: 'Controlled enterprise and government work interface',
  robots: { index: false, follow: false, nocache: true },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
