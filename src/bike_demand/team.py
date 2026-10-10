def normalize_team_slug(team_name: str) -> str:
    if team_name is None or not team_name.strip():
        raise ValueError(
            "Team name must contain at least one non-whitespace character."
        )
    # split handles all whitespaces (spaces, tabs, newlines)
    # and collapses multiples ones into one hyphen
    return "-".join(team_name.split()).lower()
