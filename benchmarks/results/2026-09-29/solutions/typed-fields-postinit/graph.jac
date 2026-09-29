obj InvoiceLine {
    has sku: str;
    has unit_price: int;
    has subtotal: int postinit;
    has quantity: int = 1;
    has tags: list[str] = [];

    def postinit {
        self.subtotal = self.unit_price * self.quantity;
    }
}