import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kreeda Hiring Bot",
  description: "AI-powered resume screening and candidate management system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        {children}
      </body>
    </html>
  );
}
