"""Small, deterministic example incident set for local development.

These records are synthetic teaching examples, not production telemetry or benchmark results.
"""

INCIDENTS = [
    {
        "id": "INC-2048",
        "title": "Checkout requests timing out",
        "service": "checkout-api",
        "severity": "Critical",
        "status": "Investigating",
        "age": "4 min ago",
        "errors": 148,
        "affected": 3,
        "summary": "Elevated checkout latency following a rise in database connection errors.",
        "signals": [
            {"time": "14:02:11", "service": "database-pool", "level": "warn", "message": "Connection pool usage reached 91%", "value": 91, "unit": "%"},
            {"time": "14:03:04", "service": "checkout-api", "level": "error", "message": "Request exceeded upstream timeout", "value": 5000, "unit": "ms"},
            {"time": "14:03:29", "service": "payment-worker", "level": "error", "message": "Payment attempt scheduled for retry", "value": 3, "unit": "retries"},
            {"time": "14:04:02", "service": "inventory-api", "level": "warn", "message": "Dependency response time above threshold", "value": 1840, "unit": "ms"},
        ],
    },
    {
        "id": "INC-2047", "title": "Inventory sync lag", "service": "inventory-worker",
        "severity": "High", "status": "Monitoring", "age": "18 min ago", "errors": 62, "affected": 2,
        "summary": "Worker queue depth is above its normal range; delayed stock updates reported.",
        "signals": [
            {"time": "13:48:03", "service": "inventory-worker", "level": "warn", "message": "Queue depth above expected range", "value": 280, "unit": "jobs"},
            {"time": "13:49:12", "service": "inventory-db", "level": "warn", "message": "Batch write duration increased", "value": 1300, "unit": "ms"},
        ],
    },
    {
        "id": "INC-2046", "title": "Authentication retry spike", "service": "auth-gateway",
        "severity": "Medium", "status": "Resolved", "age": "52 min ago", "errors": 31, "affected": 1,
        "summary": "A short burst of upstream retries caused intermittent sign-in failures.",
        "signals": [
            {"time": "13:12:10", "service": "auth-gateway", "level": "warn", "message": "Upstream retry rate exceeded baseline", "value": 18, "unit": "%"},
        ],
    },
    {
        "id": "INC-2045", "title": "Search index freshness degraded", "service": "search-indexer",
        "severity": "Low", "status": "Monitoring", "age": "1 hr ago", "errors": 19, "affected": 2,
        "summary": "Indexing throughput is below target after a batch processing delay.",
        "signals": [
            {"time": "12:46:32", "service": "search-indexer", "level": "warn", "message": "Indexing throughput below baseline", "value": 38, "unit": "%"},
        ],
    },
]

SERVICE_EDGES = [
    {"source": "api-gateway", "target": "checkout-api", "type": "request"},
    {"source": "api-gateway", "target": "inventory-api", "type": "request"},
    {"source": "checkout-api", "target": "database-pool", "type": "database"},
    {"source": "checkout-api", "target": "payment-worker", "type": "async"},
    {"source": "inventory-api", "target": "inventory-db", "type": "database"},
]
