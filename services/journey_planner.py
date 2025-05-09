import polyline
import requests
from geopy.distance import geodesic

from models import Taxi


class JourneyPlanner:
    TAXI_THRESHOLD = 3000
    ORS_API_KEY = "5b3ce3597851110001cf6248db8794c4fc8145b18145eb73dbc83845"

    def __init__(self, route_planner):
        self.route_planner = route_planner
        self.stops = {stop["id"]: (stop["lat"], stop["lon"]) for stop in route_planner.data.get("duraklar", [])}
        self.id_to_name = {stop["id"]: stop["name"] for stop in route_planner.data.get("duraklar", [])}

    def plan_journey(self, start_coords, end_coords, passenger, payment_methods):

        start_stop = self.find_nearest_stop(start_coords)
        end_stop = self.find_nearest_stop(end_coords)

        if not start_stop or not end_stop:
            return {"error": "Could not find nearby stops"}

        start_taxi_needed = start_stop["taxi_required"]
        start_taxi_cost = start_stop["taxi_cost"] if start_taxi_needed else 0
        start_taxi_time = start_stop["taxi_time"] if start_taxi_needed else 0
        start_walking_time = 0 if start_taxi_needed else self.estimate_walking_time(start_stop["distance"])

        end_taxi_needed = end_stop["taxi_required"]
        end_taxi_cost = end_stop["taxi_cost"] if end_taxi_needed else 0
        end_taxi_time = end_stop["taxi_time"] if end_taxi_needed else 0
        end_walking_time = 0 if end_taxi_needed else self.estimate_walking_time(end_stop["distance"])

        direct_taxi = self.calculate_direct_taxi(start_coords, end_coords)

        alternatives = self.route_planner.find_alternative_routes(start_stop["id"], end_stop["id"], k=4)

        processed_alternatives = []

        if direct_taxi:
            processed_alternatives.append({
                "route_type": "Direct Taxi",
                "path": ["taxi_direct"],
                "steps": [{
                    "from": "start",
                    "fromName": "Starting Location",
                    "to": "end",
                    "toName": "Destination",
                    "transportType": "taxi",
                    "distance": direct_taxi["distance"],
                    "time": direct_taxi["time"],
                    "cost": direct_taxi["cost"],
                    "transfers": 0
                }],
                "start_walking": False,
                "end_walking": False,
                "start_taxi_cost": 0,
                "end_taxi_cost": 0,
                "original_cost": direct_taxi["cost"],
                "discounted_cost": direct_taxi["cost"],  # takside yok şndirim
                "total_cost": direct_taxi["cost"],
                "total_time": direct_taxi["time"],
                "total_transfers": 0,
                "totalDistance": direct_taxi["distance"]
            })


        for alt in alternatives:

            discount = passenger.get_discount()
            transport_cost = alt["totalCost"] * (1 - discount)

            total_cost = transport_cost + start_taxi_cost + end_taxi_cost

            total_time = (alt["totalTime"] +
                          start_taxi_time + end_taxi_time +
                          start_walking_time + end_walking_time)

            route_type = self.get_route_type_name(alt["steps"])

            processed_alt = {
                "route_type": route_type,
                "path": alt["path"],
                "steps": alt["steps"],
                "start_walking": not start_taxi_needed,
                "start_taxi_cost": start_taxi_cost,
                "end_walking": not end_taxi_needed,
                "end_taxi_cost": end_taxi_cost,
                "original_cost": alt["totalCost"],
                "discounted_cost": transport_cost,
                "total_cost": total_cost,
                "total_time": total_time,
                "total_transfers": alt["totalTransfers"],
                "totalDistance": alt["totalDistance"]
            }

            for payment_method in payment_methods:
                if payment_method.can_afford(total_cost):
                    processed_alt["payment_method"] = payment_method.__class__.__name__
                    processed_alternatives.append(processed_alt)
                    break

        processed_alternatives.sort(key=lambda x: (x["total_cost"], x["total_time"], x["total_transfers"]))

        return {
            "optimal_route": processed_alternatives[0] if processed_alternatives else None,
            "alternatives": processed_alternatives,
            "direct_taxi": direct_taxi
        }

    def find_nearest_stop(self, coords):
        nearest_stop = None
        min_distance = float("inf")

        for stop_id, stop_coords in self.stops.items():
            distance = geodesic(coords, stop_coords).meters

            if distance < min_distance:
                min_distance = distance
                nearest_stop = {
                    "id": stop_id,
                    "name": self.id_to_name.get(stop_id, stop_id),
                    "lat": stop_coords[0],
                    "lon": stop_coords[1],
                    "distance": distance
                }

        if nearest_stop:
            taxi_required = nearest_stop["distance"] > self.TAXI_THRESHOLD

            if taxi_required:
                taxi = Taxi()
                nearest_stop["taxi_required"] = True
                nearest_stop["taxi_cost"] = taxi.calculate_cost(nearest_stop["distance"] / 1000)
                nearest_stop["taxi_time"] = taxi.calculate_time(nearest_stop["distance"] / 1000)
                nearest_stop["taxi_route"] = self.get_taxi_route(coords, (nearest_stop["lat"], nearest_stop["lon"]))
            else:
                nearest_stop["taxi_required"] = False
                nearest_stop["walking_route"] = self.get_walking_route(coords,
                                                                       (nearest_stop["lat"], nearest_stop["lon"]))

        return nearest_stop

    def calculate_direct_taxi(self, start_coords, end_coords):
        distance = geodesic(start_coords, end_coords).meters
        taxi = Taxi()

        return {
            "distance": distance / 1000,  # Convert to km
            "cost": taxi.calculate_cost(distance / 1000),
            "time": taxi.calculate_time(distance / 1000),
            "route": self.get_taxi_route(start_coords, end_coords)
        }

    def estimate_walking_time(self, distance_meters):

        # ortalama yürüme hızı 5 km/h = 83.33 m/dk
        return distance_meters / 83.33

    def get_route_type_name(self, steps):
        types = set(step["transportType"] for step in steps)

        if types == {"bus"}:
            return "Sadece Otobüs"
        elif types == {"tram"}:
            return "Sadece Tramvay"
        elif "bus" in types and "tram" in types:
            return "Otobüs + Tramvay Aktarması"
        elif "transfer" in types:
            return "Aktarmalı Rota"
        else:
            return "Karışık Rota"

    def get_walking_route(self, start_coords, end_coords):
        url = "https://api.openrouteservice.org/v2/directions/foot-walking"
        headers = {"Authorization": self.ORS_API_KEY, "Content-Type": "application/json"}
        payload = {
            "coordinates": [list(reversed(start_coords)), list(reversed(end_coords))],
            "format": "json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                print(f"ORS Walking API Error: {response.status_code}, {response.text}")
                return None

            route_data = response.json()

            if "routes" not in route_data or len(route_data["routes"]) == 0:
                print(f"ORS Walking Response Unexpected Format: {route_data}")
                return None

            polyline_str = route_data["routes"][0]["geometry"]
            decoded_route = polyline.decode(polyline_str)

            return decoded_route
        except Exception as e:
            print(f"Error getting walking route: {e}")
            return None

    def get_taxi_route(self, start_coords, end_coords):
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {"Authorization": self.ORS_API_KEY, "Content-Type": "application/json"}
        payload = {
            "coordinates": [list(reversed(start_coords)), list(reversed(end_coords))],
            "format": "json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                print(f"ORS Taxi API Error: {response.status_code}, {response.text}")
                return None

            route_data = response.json()

            if "routes" not in route_data or len(route_data["routes"]) == 0:
                print(f"ORS Taxi Response Unexpected Format: {route_data}")
                return None

            polyline_str = route_data["routes"][0]["geometry"]
            decoded_route = polyline.decode(polyline_str)

            return decoded_route
        except Exception as e:
            print(f"Error getting taxi route: {e}")
            return None