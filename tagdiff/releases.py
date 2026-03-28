def filter_by_range(releases, from_version=None, to_version=None):
    """Filter a chronologically-ordered release list to a version range (inclusive)."""
    ordered = list(reversed(releases))

    if from_version and to_version:
        collecting = False
        filtered = []
        for r in ordered:
            tag = r.get("tag_name")
            if tag == from_version:
                collecting = True
                filtered.append(r)
                continue
            if tag == to_version:
                filtered.append(r)
                break
            if collecting:
                filtered.append(r)
        return filtered

    if from_version:
        collecting = False
        filtered = []
        for r in ordered:
            tag = r.get("tag_name")
            if tag == from_version:
                collecting = True
            if collecting:
                filtered.append(r)
        return filtered

    if to_version:
        filtered = []
        for r in ordered:
            tag = r.get("tag_name")
            filtered.append(r)
            if tag == to_version:
                break
        return filtered

    return ordered
