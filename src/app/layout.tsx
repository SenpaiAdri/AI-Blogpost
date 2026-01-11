import type { Metadata } from "next";
import { Poppins } from "next/font/google";
import { SpeedInsights } from "@vercel/speed-insights/next";
import "./globals.css";

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "AI Blogpost | Home",
  description: "An AI-Powered Blogging Channel for Latest Tech News and Updates",
  icons: {
    icon: "/logo/ai_blogpost_text_dark.svg",
  },
  openGraph: {
    title: "AI Blogpost | Home",
    description: "An AI-Powered Blogging Channel for Latest Tech News and Updates",
    images: "/logo/ai_blogpost_text_dark.svg",
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={poppins.variable}>
      <body className="antialiased">
        {children}
        <SpeedInsights />
      </body>
    </html>
  );
}
