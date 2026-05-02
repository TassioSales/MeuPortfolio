import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CollabCanvas",
  description: "Realtime pixel art board inspired by r/place.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
