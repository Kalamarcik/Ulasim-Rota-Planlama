from abc import ABC, abstractmethod


class Payment(ABC):
    @abstractmethod
    def pay(self, amount):
        pass

    @abstractmethod
    def can_afford(self, amount):
        pass


class CashPayment(Payment):
    def __init__(self, available_cash=float('inf')):
        self.available_cash = available_cash

    def pay(self, amount):
        if self.can_afford(amount):
            self.available_cash -= amount
            return True, f"{amount} TL nakit ödendi."
        return False, "Yetersiz nakit!"

    def can_afford(self, amount):
        return self.available_cash >= amount


class CreditCardPayment(Payment):
    def __init__(self, limit=float('inf')):
        self.limit = limit

    def pay(self, amount):
        if self.can_afford(amount):
            self.limit -= amount
            return True, f"{amount} TL kredi kartı ile ödendi."
        return False, "Kredi kartı limiti yetersiz!"

    def can_afford(self, amount):
        return self.limit >= amount


class KentCardPayment(Payment):
    def __init__(self, balance):
        self.balance = balance

    def pay(self, amount):
        if self.can_afford(amount):
            self.balance -= amount
            return True, f"{amount} TL KentKart ile ödendi. Yeni bakiye: {self.balance} TL"
        return False, "Yetersiz bakiye!"

    def can_afford(self, amount):
        return self.balance >= amount

    def top_up(self, amount):
        self.balance += amount
        return f"KentKart bakiyesi {amount} TL arttırıldı. Yeni bakiye: {self.balance} TL"