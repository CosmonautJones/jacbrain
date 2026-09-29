node Offer {
    has title: str = "Lunch";
}

walker FindOffers {
    can start with Root entry {
        visit [-->];
    }
    can found with Offer entry {
        report here.title;
    }
}
