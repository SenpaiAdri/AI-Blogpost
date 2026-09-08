"""RSS feed registry (no third-party deps). Imported by feeds and health-check scripts.

Relevance scope: AI + software engineering (+ security only with an AI/dev
angle). The keyword filter in relevance.py is the primary gate: general-tech,
pure security/infra, quantum/robotics, and enterprise/SaaS items without an
AI/SWE co-signal are rejected even if their feed is listed here. When
`rss_sources` rows exist in Supabase, orchestrator prefers those DB feeds over
this hardcoded fallback — curate the DB table toward AI/SWE sources too.
"""

RSS_FEEDS = [
    # --- Core AI / SWE signal (keep) ---
    {"name": "GitHub Blog", "url": "https://github.blog/feed/"},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
    {"name": "DeepMind Blog", "url": "https://deepmind.google/blog/rss.xml"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss"},
    {"name": "Hacker News Best", "url": "https://hnrss.org/best"},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    {"name": "NVIDIA Blog", "url": "https://blogs.nvidia.com/feed/"},
    {"name": "NVIDIA Newsroom", "url": "https://nvidianews.nvidia.com/rss"},
    {"name": "AWS Blog", "url": "https://aws.amazon.com/blogs/aws/feed/"},
    # --- General tech (kept for AI/SWE stories; filter rejects the rest) ---
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "Engadget", "url": "https://www.engadget.com/rss.xml"},
    {"name": "CNET", "url": "https://www.cnet.com/rss/news/"},
    {"name": "ZDNet", "url": "https://www.zdnet.com/news/rss.xml"},
    {"name": "BBC Technology", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    {"name": "The Register", "url": "https://www.theregister.com/headlines.rss"},
    {"name": "VentureBeat", "url": "https://venturebeat.com/feed/"},
    # --- Security (kept; filter only passes AI/dev-angled items) ---
    {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/"},
    {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/"},
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackerNews"},
    {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml"},
    {"name": "SecurityWeek", "url": "https://www.securityweek.com/feed/"},
    # {"name": "The Cyber Post", "url": "https://thecyberpost.com/feed/"},
    # --- Disabled: out of scope for AI + SWE (+ AI/dev security) ---
    # Standalone quantum feeds produced posts with no AI/SWE angle and are
    # now rejected by the tiered filter; keep disabled to save fetch + cost.
    # {"name": "Quantum Computing Report", "url": "https://quantumcomputingreport.com/feed"},
    # {"name": "Quantum Zeitgeist", "url": "https://quantumzeitgeist.com/feed/"},
]
