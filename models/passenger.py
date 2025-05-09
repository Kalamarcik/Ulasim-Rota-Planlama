from abc import ABC, abstractmethod
import networkx as nx
import requests
import polyline
from geopy.distance import geodesic


class Passenger(ABC):
    def __init__(self, name, age):
        self.name = name
        self.age = age

    @abstractmethod
    def get_discount(self):
        pass


class GeneralPassenger(Passenger):
    def get_discount(self):
        return 0


class StudentPassenger(Passenger):
    def get_discount(self):
        return 0.5


class SeniorPassenger(Passenger):
    FREE_RIDES_LIMIT = 20

    def __init__(self, name, age):
        super().__init__(name, age)
        self.free_rides_used = 0

    def get_discount(self):
        return 1 if self.free_rides_used < self.FREE_RIDES_LIMIT else 0

    def use_free_ride(self):
        if self.free_rides_used < self.FREE_RIDES_LIMIT:
            self.free_rides_used += 1


class TeacherPassenger(Passenger):
    def get_discount(self):
        return 0.25
