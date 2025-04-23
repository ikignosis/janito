def merge_configs(*configs):
    """
    Merge multiple config-like objects (with .all()) into one dict.
    Later configs override earlier ones.
    """
    merged = {}
    for cfg in configs:
        merged.update(cfg.all())
    return merged
