

import polyline
import requests
from services.journey_planner import JourneyPlanner
from services.route_planner import RoutePlanner

from flask import Flask, render_template, request, jsonify

from models import Taxi, GeneralPassenger, CashPayment, CreditCardPayment, KentCardPayment, SeniorPassenger, \
    StudentPassenger
from models.passenger import TeacherPassenger
from services import route_planner


app = Flask(__name__)

planner = RoutePlanner("data/izmit_data.json")


ORS_API_KEY = "5b3ce3597851110001cf6248db8794c4fc8145b18145eb73dbc83845"

TAXI_THRESHOLD = 3000


def get_route_from_ors(start_coords, end_coords):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "coordinates": [start_coords[::-1], end_coords[::-1]],
        "format": "json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print("🚨 ORS API Hatası:", response.status_code, response.text)
        return None

    route_data = response.json()

    if "routes" not in route_data or len(route_data["routes"]) == 0:
        print("🚨 ORS API Yanıtı Beklenen Format Değil:", route_data)
        return None

    polyline_str = route_data["routes"][0]["geometry"]
    decoded_route = polyline.decode(polyline_str)

    return decoded_route

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/get_stops")
def get_stops():
    stops = planner.data.get("duraklar", [])
    stop_list = [{"id": stop["id"], "name": stop["name"]} for stop in stops]
    return jsonify(stop_list)


from geopy.distance import geodesic

def get_walking_route(start_coords, end_coords):
    url = "https://api.openrouteservice.org/v2/directions/foot-walking"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "coordinates": [start_coords[::-1], end_coords[::-1]],
        "format": "json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print("🚨 ORS Walking API Hatası:", response.status_code, response.text)
        return None

    route_data = response.json()

    if "routes" not in route_data or len(route_data["routes"]) == 0:
        print("🚨 ORS Walking Yanıtı Beklenen Format Değil:", route_data)
        return None

    polyline_str = route_data["routes"][0]["geometry"]
    decoded_route = polyline.decode(polyline_str)

    return decoded_route

def get_taxi_route(start_coords, end_coords):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "coordinates": [start_coords[::-1], end_coords[::-1]],
        "format": "json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print("🚨 ORS Taksi API Hatası:", response.status_code, response.text)
        return None

    route_data = response.json()

    if "routes" not in route_data or len(route_data["routes"]) == 0:
        print("🚨 ORS Taksi Yanıtı Beklenen Format Değil:", route_data)
        return None

    polyline_str = route_data["routes"][0]["geometry"]
    decoded_route = polyline.decode(polyline_str)

    return decoded_route

@app.route("/find_nearest_stop", methods=["POST"])
def find_nearest_stop():
    data = request.json
    user_coords = (data["lat"], data["lon"])

    stops = planner.data.get("duraklar", [])
    nearest_stop = None
    min_distance = float("inf")

    for stop in stops:
        stop_coords = (stop["lat"], stop["lon"])
        distance = geodesic(user_coords, stop_coords).meters

        if distance < min_distance:
            min_distance = distance
            nearest_stop = stop

    if nearest_stop is None:
        return jsonify({"error": "En yakın durak bulunamadı."}), 404

    taxi_required = min_distance > TAXI_THRESHOLD
    taxi_route = None
    taxi_cost = 0
    taxi_time = 0

    if taxi_required:
        taxi = Taxi()
        taxi_cost = taxi.calculate_cost(min_distance / 1000)
        taxi_time = taxi.calculate_time(min_distance / 1000)
        taxi_route = get_taxi_route(user_coords, (nearest_stop["lat"], nearest_stop["lon"]))

    return jsonify({
        "id": nearest_stop["id"],
        "name": nearest_stop["name"],
        "lat": nearest_stop["lat"],
        "lon": nearest_stop["lon"],
        "distance": min_distance,
        "walking_route": None if taxi_required else get_walking_route(user_coords, (nearest_stop["lat"], nearest_stop["lon"])),
        "taxi_required": taxi_required,
        "taxi_cost": taxi_cost,
        "taxi_time": taxi_time,
        "taxi_route": taxi_route
    })



@app.route("/find_nearest_stop_for_destination", methods=["POST"])
def find_nearest_stop_for_destination():
    data = request.json
    user_coords = (data["lat"], data["lon"])

    stops = planner.data.get("duraklar", [])
    nearest_stop = None
    min_distance = float("inf")

    for stop in stops:
        stop_coords = (stop["lat"], stop["lon"])
        distance = geodesic(user_coords, stop_coords).meters

        if distance < min_distance:
            min_distance = distance
            nearest_stop = stop

    if nearest_stop is None:
        return jsonify({"error": "En yakın durak bulunamadı."}), 404

    taxi_required = min_distance > TAXI_THRESHOLD
    taxi_route = None
    taxi_cost = 0
    taxi_time = 0

    if taxi_required:
        taxi = Taxi()
        taxi_cost = taxi.calculate_cost(min_distance / 1000)
        taxi_time = taxi.calculate_time(min_distance / 1000)
        taxi_route = get_taxi_route(user_coords, (nearest_stop["lat"], nearest_stop["lon"]))

    return jsonify({
        "id": nearest_stop["id"],
        "name": nearest_stop["name"],
        "lat": nearest_stop["lat"],
        "lon": nearest_stop["lon"],
        "distance": min_distance,
        "walking_route": None if taxi_required else get_walking_route(user_coords, (nearest_stop["lat"], nearest_stop["lon"])),
        "taxi_required": taxi_required,
        "taxi_cost": taxi_cost,
        "taxi_time": taxi_time,
        "taxi_route": taxi_route
    })




@app.route("/get_routes", methods=["POST"])
def get_routes():
    data = request.json
    start = data.get("start")
    end = data.get("end")

    if not start or not end:
        return jsonify({"error": "Başlangıç ve hedef durak belirtilmelidir."}), 400

    stops = {stop["id"]: (stop["lat"], stop["lon"]) for stop in planner.data.get("duraklar", [])}

    if start not in stops or end not in stops:
        return jsonify({"error": "Seçilen duraklar bulunamadı."}), 400

    path, _ = planner.find_route(start, end)
    if not path:
        return jsonify({"error": "Rota bulunamadı."}), 404

    full_route = []
    for i in range(len(path) - 1):
        coord1 = stops[path[i]]
        coord2 = stops[path[i + 1]]
        segment = get_route_from_ors(coord1, coord2)
        if segment:
            full_route.extend(segment)

    steps, total_cost, total_time, total_transfers, total_distance = planner.get_route_details(path)

    return jsonify({
        "route": full_route,
        "details": {
            "steps": steps,
            "totalCost": total_cost,
            "totalTime": total_time,
            "totalTransfers": total_transfers,
            "totalDistance": total_distance
        }
    })

@app.route("/get_alternative_routes", methods=["POST"])
def get_alternative_routes():
    data = request.json
    start = data.get("start")
    end = data.get("end")

    if not start or not end:
        return jsonify({"error": "Başlangıç ve hedef durak belirtilmelidir."}), 400

    alternatives = planner.find_alternative_routes(start, end, k=4)

    stops = {stop["id"]: (stop["lat"], stop["lon"]) for stop in planner.data.get("duraklar", [])}

    def get_route_type_name(steps):
        types = set()
        for step in steps:
            types.add(step["transportType"])

        if types == {"bus"}:
            return "Sadece Otobüs"
        elif types == {"tram"}:
            return "Sadece Tramvay"
        elif "bus" in types and "tram" in types:
            return "Otobüs + Tramvay Aktarması"
        elif "taxi" in types:
            return "Taksi + Otobüs veya Tramvay Kombinasyonu"
        else:
            return "Karışık Rota"

    formatted = []
    for alt in alternatives:
        coords = [stops[stop_id] for stop_id in alt["path"]]
        formatted.append({
            "name": get_route_type_name(alt["steps"]),
            "type": "mixed",
            "route": coords,
            "cost": alt["totalCost"],
            "time": alt["totalTime"],
            "distance": alt["totalDistance"],
            "transfers": alt["totalTransfers"]
        })

    return jsonify({"alternatives": formatted})


@app.route("/plan_journey", methods=["POST"])
def plan_journey():
    data = request.json

    start_coords = (data.get("start_lat"), data.get("start_lon"))
    end_coords = (data.get("end_lat"), data.get("end_lon"))

    passenger_type = data.get("passenger_type", "general")
    passenger_name = data.get("passenger_name", "Anonymous")
    passenger_age = data.get("passenger_age", 30)

    if passenger_type == "student":
        passenger = StudentPassenger(passenger_name, passenger_age)
    elif passenger_type == "senior":
        passenger = SeniorPassenger(passenger_name, passenger_age)
    elif passenger_type == "teacher":
        passenger = TeacherPassenger(passenger_name, passenger_age)
    else:
        passenger = GeneralPassenger(passenger_name, passenger_age)

    payment_methods = []

    if "cash" in data.get("payment_methods", []):
        cash_amount = data.get("cash_amount", float('inf'))
        payment_methods.append(CashPayment(cash_amount))

    if "credit_card" in data.get("payment_methods", []):
        credit_limit = data.get("credit_limit", float('inf'))
        payment_methods.append(CreditCardPayment(credit_limit))

    if "kent_card" in data.get("payment_methods", []):
        kent_card_balance = data.get("kent_card_balance", 0)
        payment_methods.append(KentCardPayment(kent_card_balance))

    journey_planner = JourneyPlanner(route_planner)
    journey = journey_planner.plan_journey(start_coords, end_coords, passenger, payment_methods)

    return jsonify(journey)

@app.route("/get_payment_options", methods=["GET"])
def get_payment_options():
    return jsonify({
        "payment_types": [
            {"id": "cash", "name": "Nakit"},
            {"id": "credit_card", "name": "Kredi Kartı"},
            {"id": "kent_card", "name": "KentKart"}
        ]
    })

@app.route("/get_passenger_types", methods=["GET"])
def get_passenger_types():
    return jsonify({
        "passenger_types": [
            {"id": "general", "name": "Genel Yolcu", "discount": 0},
            {"id": "student", "name": "Öğrenci", "discount": 50},
            {"id": "teacher", "name": "Öğretmen", "discount": 25},
            {"id": "senior", "name": "65+ Yaş", "discount": 100, "limit": 20}
        ]
    })


if __name__ == "__main__":
    app.run(debug=True)
