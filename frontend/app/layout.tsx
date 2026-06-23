import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Appointment Voice SaaS",
  description: "Owner dashboard for salon and barber appointment booking.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
