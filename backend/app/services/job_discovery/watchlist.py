"""Default company watchlist. Board tokens were probed against the public APIs.

Companies without a public Greenhouse/Lever/Ashby board are listed with ats="manual" and disabled:
their career sites use proprietary systems and are not scraped. Add them from the dashboard if a
supported board is found later.
"""
# (name, ats, board_token, region, priority)
VERIFIED = [
    ("Stripe", "greenhouse", "stripe", "global", 2), ("Cloudflare", "greenhouse", "cloudflare", "global", 2),
    ("GitLab", "greenhouse", "gitlab", "global", 2), ("Figma", "greenhouse", "figma", "global", 2),
    ("Databricks", "greenhouse", "databricks", "global", 1), ("Elastic", "greenhouse", "elastic", "global", 3),
    ("Snowflake", "ashby", "snowflake", "global", 2),
    ("Razorpay", "greenhouse", "razorpaysoftwareprivatelimited", "india", 1),
    ("Groww", "greenhouse", "groww", "india", 1), ("InMobi", "greenhouse", "inmobi", "india", 2),
    ("Druva", "greenhouse", "druva", "india", 2), ("CRED", "lever", "cred", "india", 1),
    ("Meesho", "lever", "meesho", "india", 1), ("Freshworks", "lever", "freshworks", "india", 2),
]
MANUAL = [
    "Google", "Microsoft", "Amazon", "Atlassian", "Adobe", "Salesforce", "Oracle", "NVIDIA", "Uber", "Intuit",
    "Flipkart", "PhonePe", "Swiggy", "Zomato", "Zepto", "Postman", "BrowserStack", "Zoho", "Juspay",
    "Chargebee", "Hasura",
]
INDIA_MANUAL = {"Flipkart", "PhonePe", "Swiggy", "Zomato", "Zepto", "Postman", "BrowserStack", "Zoho",
                "Juspay", "Chargebee", "Hasura"}
