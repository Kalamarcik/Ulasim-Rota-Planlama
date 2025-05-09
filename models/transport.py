from abc import ABC, abstractmethod


class Transport(ABC):
    def __init__(self, name, speed, cost_per_km):
        self.name = name
        self.speed = speed
        self.cost_per_km = cost_per_km

    @abstractmethod
    def calculate_cost(self, distance):
        pass

    @abstractmethod
    def calculate_time(self, distance):
        pass


class Bus(Transport):
    def __init__(self):
        super().__init__("Otobüs", speed=40, cost_per_km=2)

    def calculate_cost(self, distance):
        return self.cost_per_km * distance

    def calculate_time(self, distance):
        return distance / self.speed * 60


class Tram(Transport):
    def __init__(self):
        super().__init__("Tramvay", speed=50, cost_per_km=1.5)

    def calculate_cost(self, distance):
        return self.cost_per_km * distance

    def calculate_time(self, distance):
        return distance / self.speed * 60


class Taxi(Transport):
    BASE_FARE = 10  

    def __init__(self):
        super().__init__("Taksi", speed=60, cost_per_km=4)

    def calculate_cost(self, distance):
        return self.BASE_FARE + (self.cost_per_km * distance)

    def calculate_time(self, distance):
        return distance / self.speed * 60
