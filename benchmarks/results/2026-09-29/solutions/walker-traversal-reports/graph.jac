walker CollectEnabled {
    has names: list[str] = [];
    has reports: list[list[str]] = [];

    can on_root with Root entry {
        self.names = [];
        visit [-->];
    }

    can on_item with Item entry {
        if here.enabled {
            self.names.append(here.name);
        }
        visit [-->];
    }

    can finish with Root exit {
        report sorted(self.names);
    }
}