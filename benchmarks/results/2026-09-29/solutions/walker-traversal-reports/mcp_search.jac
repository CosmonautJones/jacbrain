walker CollectEnabled reports list[str] {
    has names: list[str] = [];

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

    can finish with exit {
        report sorted(self.names);
    }
}