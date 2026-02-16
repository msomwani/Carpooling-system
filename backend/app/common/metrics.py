from collections import defaultdict

metrics_store = defaultdict(int)


def increment(metric_name: str):
    metrics_store[metric_name] += 1


def get_metrics():
    return dict(metrics_store)
