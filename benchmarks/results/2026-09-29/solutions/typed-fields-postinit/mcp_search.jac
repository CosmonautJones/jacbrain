obj InvoiceLine {
    has sku: str;
    has unit_price: int;
    has quantity: int = 1;
    has tags: list[str] = [];
    has subtotal: int by postinit;

    can postinit() {
        self.subtotal = self.unit_price * self.quantity;
    }
}