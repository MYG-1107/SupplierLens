import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SupplierLens — Supplier verification workspace",
  description: "Evidence-first supplier verification, document reconciliation and explainable procurement review.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
