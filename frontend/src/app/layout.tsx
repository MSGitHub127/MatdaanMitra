import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Matdaan Mitra - Your Voter Registration Assistant',
  description: 'Intelligent, conversational guide to navigating the Indian election process.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <div className="tricolor-header" />
        <div className="grain-overlay" />
        {children}
      </body>
    </html>
  );
}
