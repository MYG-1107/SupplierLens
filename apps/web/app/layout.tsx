import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SupplierLens — Evidence-first supplier verification",
  description: "A procurement workspace for reconciling supplier evidence and surfacing explainable verification findings.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
