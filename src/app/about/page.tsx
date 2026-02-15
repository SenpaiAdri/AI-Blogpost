"use client";

import Navbar from "@/components/Navbar";
import TransitionLink from "@/components/TransitionLink";
import Marquee from "@/components/Marquee";
import BrutalBlock from "@/components/BrutalBlock";
import BrutalStat from "@/components/BrutalStat";
import TechRow from "@/components/TechRow";

export default function About() {

  return (
    <div className="min-h-screen w-full bg-[#131316] text-white">
      <Navbar />
      <div className="w-full flex justify-center">
        <main
          className="w-full border-x-2 border-[#6A6B70] border-dashed min-h-screen pt-19 pb-10
                    sm:pb-20 sm:pt-21
                    md:pt-24"
        >
          {/* ── HERO: Giant typography ── */}
          <section className="relative overflow-hidden px-6 sm:px-10 md:px-16 lg:px-24 xl:px-32 py-16 sm:py-24 lg:py-32">
            {/* grid background */}
            <div
              className="absolute inset-0 opacity-[0.2] pointer-events-none"
              style={{
                backgroundImage: `
                                    linear-gradient(to right, #6A6B70 1px, transparent 1px),
                                    linear-gradient(to bottom, #6A6B70 1px, transparent 1px)
                                `,
                backgroundSize: "80px 80px",
              }}
            />

            <div className="relative z-10 flex flex-col lg:flex-row lg:items-end lg:justify-between gap-8 lg:gap-16">
              <div className="w-full lg:w-auto lg:flex-1">
                <p className="text-[10px] sm:text-xs lg:text-sm font-bold uppercase tracking-[0.3em] text-[#6A6B70] mb-4 sm:mb-6">
                  [ABOUT]
                </p>

                <h1 className="text-6xl sm:text-8xl md:text-[120px] lg:text-[160px] xl:text-[200px] font-bold uppercase leading-[0.82] tracking-tighter">
                  <span className="block text-white">AI</span>
                </h1>
                <h1 className="text-6xl sm:text-8xl md:text-[120px] lg:text-[160px] xl:text-[200px] font-bold uppercase leading-[0.82] tracking-tighter">
                  <span
                    className="block text-transparent"
                    style={{ WebkitTextStroke: "2px #6A6B70" }}
                  >
                    BLOG
                  </span>
                </h1>
                <h1 className="text-6xl sm:text-8xl md:text-[120px] lg:text-[160px] xl:text-[200px] font-bold uppercase leading-[0.82] tracking-tighter">
                  <span className="block text-[#FF0000]">POST</span>
                </h1>
              </div>

              <div className="lg:max-w-md lg:pb-4">
                <div className="flex items-start gap-4 sm:gap-6">
                  <div className="w-16 sm:w-20 border-t-2 border-dashed border-[#FF0000] mt-3 flex-shrink-0" />
                  <p className="text-sm sm:text-base lg:text-lg text-[#808080] leading-relaxed">
                    An autonomous, AI-powered blogging website that create
                    and publishes the latest tech news every single day.
                    No humans. No delays. Just cron job.
                  </p>
                </div>
              </div>
            </div>

            {/* Corner markers — dashed */}
            <div className="absolute top-6 right-6 sm:top-8 sm:right-10 text-[#393A41]">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="4 3">
                <path d="M7 2H2v5M17 2h5v5M7 22H2v-5M17 22h5v-5" />
              </svg>
            </div>
          </section>

          {/* ── MARQUEE 1 — dashed stroke text ── */}
          <Marquee text="AI-POWERED INSIGHTS" />

          {/* ── CONTENT GRID ── */}
          <section className="px-6 sm:px-10 md:px-16 lg:px-24 xl:px-32 py-10 sm:py-14 lg:py-16 space-y-5 sm:space-y-6 lg:space-y-8">
            {/* Mission */}
            <BrutalBlock label="MISSION" accent delay={0}>
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 lg:gap-16">
                <p className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white leading-tight tracking-tight">
                  We believe tech news should be
                  <span className="text-[#FF0000]"> accessible</span>,
                  <span className="text-[#FF0000]"> concise</span>, and
                  <span className="text-[#FF0000]"> autonomous</span>.
                </p>
                <p className="text-sm sm:text-base text-[#808080] leading-relaxed lg:max-w-md flex-shrink-0">
                  No editorial bias. No information overload. Our AI reads through
                  the noise from 12+ sources and distills it into clear, actionable
                  posts — published automatically, every single day.
                </p>
              </div>
            </BrutalBlock>

            {/* Stats row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-5 lg:gap-6">
              <BrutalStat number="150" suffix="+" label="Posts Published" />
              <BrutalStat number="30" suffix="+" label="Topics Covered" />
              <BrutalStat number="12" suffix="" label="Sources Monitored" />
              <BrutalStat number="6" suffix="h" label="Run Interval" />
            </div>

            {/* Three column: Tech + Pipeline + Manifesto */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 sm:gap-6 lg:gap-8">
              {/* Tech Stack */}
              <BrutalBlock label="TECH.STACK" delay={100}>
                <TechRow name="Next.js" version="v16" role="Framework" />
                <TechRow name="Supabase" version="v2" role="Database" />
                <TechRow name="Gemini AI" version="—" role="AI Engine" />
                <TechRow name="Tailwind" version="v4" role="Styling" />
                <TechRow name="Vercel" version="—" role="Hosting" />
              </BrutalBlock>

              {/* Pipeline */}
              <BrutalBlock label="PIPELINE" delay={200}>
                <div className="space-y-5 sm:space-y-6">
                  {[
                    {
                      step: "01",
                      title: "INGEST",
                      desc: "RSS feeds from 12+ tech sources are monitored and fetched every 6 hours.",
                    },
                    {
                      step: "02",
                      title: "PROCESS",
                      desc: "Gemini AI reads, analyzes, and writes a TL;DR-style summary post.",
                    },
                    {
                      step: "03",
                      title: "PUBLISH",
                      desc: "The post is stored in Supabase and instantly live — zero human intervention.",
                    },
                  ].map((item) => (
                    <div key={item.step} className="flex gap-4 group">
                      <span className="text-3xl sm:text-4xl lg:text-5xl font-bold text-[#393A41] group-hover:text-[#FF0000] transition-colors leading-none tracking-tighter">
                        {item.step}
                      </span>
                      <div>
                        <p className="text-sm sm:text-base font-bold text-white uppercase tracking-wider">
                          {item.title}
                        </p>
                        <p className="text-xs sm:text-sm text-[#808080] mt-1 leading-relaxed">
                          {item.desc}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </BrutalBlock>

              {/* Manifesto */}
              <BrutalBlock label="MANIFESTO" delay={300}>
                <div className="space-y-6">
                  <div className="space-y-4">
                    {[
                      "Automate the boring parts.",
                      "Surface the signal from the noise.",
                      "Publish without permission.",
                      "Move fast, break nothing.",
                    ].map((line, i) => (
                      <p
                        key={i}
                        className="text-sm sm:text-base lg:text-lg font-bold text-white flex items-center gap-3"
                      >
                        <span className="w-2.5 h-2.5 bg-[#FF0000] flex-shrink-0" />
                        {line}
                      </p>
                    ))}
                  </div>
                  <div className="border-t border-dashed border-[#393A41] pt-5">
                    <p className="text-xs sm:text-sm text-[#6A6B70] leading-relaxed">
                      This project exists to prove a simple thesis: AI can manage an
                      entire content pipeline — from discovery to publication — without
                      any human in the loop. Every post you read here was written,
                      formatted, and published by an autonomous AI system.
                    </p>
                  </div>
                </div>
              </BrutalBlock>
            </div>
          </section>

          {/* ── MARQUEE 2 — dashed stroke text ── */}
          <Marquee text="AI-BLOGPOST" reverse />

          {/* ── Creator ── */}
          <section className="px-6 sm:px-10 md:px-16 lg:px-24 xl:px-32 py-10 sm:py-14 lg:py-16">
            <BrutalBlock label="CREATOR" accent delay={0}>
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 sm:gap-10 lg:gap-16">
                <div className="w-20 h-20 sm:w-24 sm:h-24 lg:w-40 lg:h-28 border-2 border-dashed border-[#FF0000] flex items-center justify-center flex-shrink-0 bg-[#FF0000]/5">
                  <span className="text-4xl sm:text-5xl lg:text-6xl font-bold text-[#FF0000]">
                    A
                  </span>
                </div>
                <div>
                  <p className="text-xl sm:text-2xl lg:text-3xl font-bold text-white tracking-tight">
                    Adrian
                  </p>
                  <p className="text-xs sm:text-sm uppercase tracking-[0.15em] text-[#6A6B70] font-bold mb-3">
                    Full-Stack Developer
                  </p>
                  <p className="text-sm sm:text-base text-[#808080] leading-relaxed max-w-2xl">
                    This project is built out of curiosity as i found other developer has a blog post integrated to their portfolio. So I thought it was a good idea to have a blog post integrated to my portfolio.
                    So I thought, why not we make a blog post that is autonomous and can be published by an AI system.
                    And so this is how the project started.
                    <br /><br />
                    AI Blogpost autonomously run an entire content pipeline — from RSS ingestion to final publication. No editorial team needed. Every post you see was discovered, written, and published
                    by an autonomous AI system.
                  </p>
                </div>
              </div>
            </BrutalBlock>
          </section>

          {/* ── Footer ── */}
          <div className="border-t-2 border-dashed border-[#6A6B70] px-6 sm:px-10 md:px-16 lg:px-24 xl:px-32 py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-[10px] sm:text-xs font-bold uppercase tracking-[0.2em] text-[#393A41]">
              © 2025 AI Blogpost — All systems autonomous
            </p>
            <TransitionLink
              href="/"
              className="text-xs sm:text-sm font-bold text-[#6A6B70] hover:text-[#FF0000] transition-colors inline-flex items-center gap-2 uppercase tracking-wider"
            >
              <svg
                className="w-4 h-4 rotate-180"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
              Back to blog
            </TransitionLink>
          </div>
        </main>
      </div>
    </div>
  );
}