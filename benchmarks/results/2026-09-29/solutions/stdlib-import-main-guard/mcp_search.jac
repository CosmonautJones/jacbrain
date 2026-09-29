import:py from datetime { date }

def days_between(start: str, end: str) -> int {
    start_date = date.fromisoformat(start);
    end_date = date.fromisoformat(end);
    if start_date.isoformat() != start or end_date.isoformat() != end {
        raise ValueError("Dates must use YYYY-MM-DD format");
    }
    return (end_date - start_date).days;
}

with entry:__main__ {
    print("date helper ready");
}
