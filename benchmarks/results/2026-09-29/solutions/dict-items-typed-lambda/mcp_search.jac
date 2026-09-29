def rank_scores(scores: dict[str, int], minimum: int) -> list[str] {
    eligible: list[tuple[str, int]] = [];
    for (name, score) in scores.items() {
        if score >= minimum {
            eligible.append((name, score));
        }
    }
    ranked = sorted(eligible, key=lambda entry: tuple[str, int] -> tuple[int, str]: (-entry[1], entry[0]));
    names: list[str] = [];
    for (name, score) in ranked {
        names.append(name);
    }
    return names;
}