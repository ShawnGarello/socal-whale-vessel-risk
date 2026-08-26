import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SoCal whale–vessel spatial overlap",
  description:
    "Exploratory GIS application for the Southern California blue-whale habitat and commercial vessel activity overlap analysis.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
