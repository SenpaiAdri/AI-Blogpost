import type { Metadata } from "next";
import { Poppins } from "next/font/google";
import "./globals.css";
import { SpeedInsights } from "@vercel/speed-insights/next"
import PageTransitionProvider from "@/components/PageTransitionProvider";
import ThemeProvider from "@/components/ThemeProvider";

const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("ai-blogpost-theme");if(t==="light"||t==="dark"){if(t==="dark")document.documentElement.classList.add("dark");else document.documentElement.classList.remove("dark")}else if(window.matchMedia("(prefers-color-scheme: dark)").matches){document.documentElement.classList.add("dark")}else{document.documentElement.classList.remove("dark")}}catch(e){}})();`;

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://ai-blogpost.vercel.app"),
  title: {
    default: "AI Blogpost",
    template: "%s | AI Blogpost",
  },
  description: "An AI-Powered Blogging Channel for Latest Tech News and Updates",
  keywords: [
    "AI Blogpost",
    "AI Blogging",
    "AI News",
    "AI Updates",
    "AI Technology",
    "AI Development",
    "AI Tools",
    "AI Automation",
    "AI Integration",
    "AI Solutions",
  ],
  authors: [{ name: "Adrian" }],
  creator: "Adrian",
  icons: {
    icon: "/logo/logo_site_icon.png",
    apple: "/logo/logo_site_icon.png",
  },
  openGraph: {
    title: "AI Blogpost | Home",
    description: "An AI-Powered Blogging Channel for Latest Tech News and Updates",
    images: "/logo/ai_blogpost_light.png",
    url: "https://ai-blogpost.vercel.app",
    siteName: "AI Blogpost",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "AI Blogpost",
    description: "An AI-Powered Blogging Channel for Latest Tech News and Updates",
    images: "/logo/ai_blogpost_light.png",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={poppins.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="antialiased">
        <ThemeProvider>
          <PageTransitionProvider>{children}</PageTransitionProvider>
        </ThemeProvider>
        <SpeedInsights />
      </body>
    </html>
  );
}
