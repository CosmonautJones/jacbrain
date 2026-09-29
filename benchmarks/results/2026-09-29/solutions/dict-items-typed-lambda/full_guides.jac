def rank_scores(scores: dict[str, int], minimum: int) -> list[str] {
    eligible: list[tuple[str, int]] = [];
    for (name, score) in scores.items() {
        if score >= minimum {
            eligible.append((name, score));
        }
    }
    ranked = sorted(eligible, key=lambda (item: tuple[str, int]) -> tuple[int, str] {
        return (~item[1], item[0]);
    });
    return [item[0] for item in ranked];
}