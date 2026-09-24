"""RSS feeds for the daily digest.

Each section has a list of (source name, feed URL) pairs.
If a section has "keywords", only articles whose title or summary contains
one of them are kept (useful for broad news sites). Leave it empty to keep all.
"""

SECTIONS = [
    {
        "title": "AI & Research",
        "max_items": 6,
        "keywords": [],
        "feeds": [
            ("Google Research", "https://research.google/blog/rss/"),
            ("OpenAI", "https://openai.com/news/rss.xml"),
            ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
            ("BAIR (Berkeley)", "https://bair.berkeley.edu/blog/feed.xml"),
            ("MIT News AI", "https://news.mit.edu/rss/topic/artificial-intelligence2"),
        ],
    },
    {
        "title": "How Big Tech Builds Things",
        "max_items": 6,
        "keywords": [],
        "feeds": [
            ("Netflix Tech Blog", "https://netflixtechblog.com/feed"),
            # Uber removed its RSS feed; Grab and Lyft cover the same ride-hailing/delivery problems.
            ("Grab Engineering", "https://engineering.grab.com/feed.xml"),
            ("Lyft Engineering", "https://eng.lyft.com/feed"),
            ("Meta Engineering", "https://engineering.fb.com/feed/"),
            ("Airbnb Engineering", "https://medium.com/feed/airbnb-engineering"),
            ("Cloudflare Blog", "https://blog.cloudflare.com/rss/"),
            ("Spotify Engineering", "https://engineering.atspotify.com/feed/"),
            ("Pinterest Engineering", "https://medium.com/feed/pinterest-engineering"),
            ("Dropbox Tech", "https://dropbox.tech/feed"),
            ("ByteByteGo", "https://blog.bytebytego.com/feed"),
        ],
    },
    {
        "title": "Top Tech News",
        "max_items": 6,
        "keywords": [],
        "feeds": [
            ("Hacker News (100+ points)", "https://hnrss.org/frontpage?points=100"),
            ("TechCrunch", "https://techcrunch.com/feed/"),
            ("The Verge", "https://www.theverge.com/rss/index.xml"),
            ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
        ],
    },
    {
        "title": "Manufacturing",
        "max_items": 4,
        "keywords": [
            "predictive maintenance", "iiot", "industrial iot", "digital twin",
            "computer vision", "automation", "sensor", "ai", "robot", "smart factory",
            "machine learning", "software", "data",
        ],
        "feeds": [
            ("Manufacturing Dive", "https://www.manufacturingdive.com/feeds/news/"),
            ("IoT Analytics", "https://iot-analytics.com/feed/"),
            ("The Robot Report", "https://www.therobotreport.com/feed/"),
        ],
    },
    {
        "title": "Fleets & Logistics",
        "max_items": 4,
        "keywords": [
            "route", "routing", "telematics", "forecast", "warehouse", "automation",
            "ai", "software", "technology", "tech", "autonomous", "robot", "data",
            "visibility", "platform",
        ],
        "feeds": [
            ("FreightWaves", "https://www.freightwaves.com/news/feed"),
            ("Supply Chain Dive", "https://www.supplychaindive.com/feeds/news/"),
            ("Logistics Viewpoints", "https://logisticsviewpoints.com/feed/"),
        ],
    },
    {
        "title": "Real Estate & PropTech",
        "max_items": 4,
        "keywords": [
            "proptech", "ai", "valuation", "smart building", "software", "platform",
            "technology", "tech", "data", "automation", "startup",
        ],
        "feeds": [
            ("HousingWire", "https://www.housingwire.com/feed/"),
            ("Propmodo", "https://www.propmodo.com/feed/"),
            ("Inman", "https://feeds.feedburner.com/inmannews"),
        ],
    },
]

# Topics for the "Concept of the Day" (only used when a Claude API key is set).
# One is picked per day, cycling through the list.
CONCEPTS = [
    "Caching (CDNs, Redis) and how Netflix serves video fast",
    "Load balancing and how Uber handles millions of ride requests",
    "Message queues and Kafka: streaming data between services",
    "Database sharding and replication",
    "The vehicle routing problem and route optimization",
    "Predictive maintenance with sensor data and anomaly detection",
    "Recommendation systems: how Netflix and Zillow suggest what you'll like",
    "Microservices vs monoliths",
    "Time-series databases for IoT and telematics",
    "Transformers and how large language models work",
    "Retrieval-augmented generation (RAG)",
    "Computer vision for quality inspection",
    "Demand forecasting (how Blinkit and Zepto stock dark stores)",
    "Geospatial indexing (H3, geohash) for maps and delivery apps",
    "Rate limiting and API gateways",
    "Event-driven architecture",
    "Digital twins in manufacturing",
    "Automated valuation models (AVMs) and Zillow's model-risk lesson",
    "A/B testing and experimentation platforms",
    "Vector databases and embeddings",
    "CAP theorem and consistency in distributed systems",
    "Batch vs stream processing (Spark vs Flink)",
    "Search engines: inverted indexes and ranking",
    "Observability: logs, metrics and traces",
]
