walker CollectEnabled {
    has names: list[str] = [];
    has reports: list[list[str]] = [];

    can start with Root entry {
        self.names = [];
        visit [-->];
    }

    can collect with Item entry {
        if here.enabled {
            self.names.append(here.name);
        }
        visit [-->];
    }

    can finish with Root exit {
        report sorted(self.names);
    }
}