import networkx as nx

from services.data_loader import DataLoader


class RoutePlanner:
    def __init__(self, json_file):
        self.data = DataLoader.load_json(json_file)
        self.graph = nx.DiGraph()
        self.load_graph()

    def load_graph(self):
        if not self.data:
            return

        stops = self.data.get("duraklar", [])

        for stop in stops:
            stop_id = stop["id"]

            for next_stop in stop.get("nextStops", []):
                self.graph.add_edge(stop_id, next_stop["stopId"],
                                    weight=next_stop["mesafe"],
                                    time=next_stop["sure"],
                                    cost=next_stop["ucret"],
                                    transfers=0)

            transfer = stop.get("transfer")
            if transfer:
                self.graph.add_edge(stop_id, transfer["transferStopId"],
                                    weight=0.5,
                                    time=transfer["transferSure"],
                                    cost=transfer["transferUcret"],
                                    transfers=1)

    def find_route(self, start, end, weight="weight"):
        if start not in self.graph or end not in self.graph:
            return None, None

        try:
            path = nx.shortest_path(self.graph, source=start, target=end, weight=weight)
            total_weight = sum(self.graph[u][v][weight] for u, v in zip(path[:-1], path[1:]))
            return path, total_weight
        except nx.NetworkXNoPath:
            return None, None

    def find_alternative_routes(self, start, end, k=4, weight="weight"):
        if start not in self.graph or end not in self.graph:
            return []

        try:
            paths = list(nx.shortest_simple_paths(self.graph, source=start, target=end, weight=weight))
            alternatives = []

            for path in paths[:k]:
                steps, cost, time, transfers, distance = self.get_route_details(path)
                alternatives.append({
                    "path": path,
                    "steps": steps,
                    "totalCost": cost,
                    "totalTime": time,
                    "totalTransfers": transfers,
                    "totalDistance": distance
                })

            return alternatives
        except nx.NetworkXNoPath:
            return []

    def get_route_details(self, path):
        details = []
        total_cost, total_time, total_transfers, total_distance = 0, 0, 0, 0

        id_to_name = {stop["id"]: stop["name"] for stop in self.data.get("duraklar", [])}

        def get_transport_type(from_id, to_id, transfers):
            if transfers > 0:
                return "transfer"
            from_type = from_id.split("_")[0]
            to_type = to_id.split("_")[0]
            if from_type == to_type:
                return from_type
            return "transfer"

        for i in range(len(path) - 1):
            start, end = path[i], path[i + 1]
            edge_data = self.graph.get_edge_data(start, end)

            transport_type = get_transport_type(start, end, edge_data["transfers"])

            details.append({
                "from": start,
                "fromName": id_to_name.get(start, start),
                "to": end,
                "toName": id_to_name.get(end, end),
                "transportType": transport_type,
                "distance": edge_data["weight"],
                "time": edge_data["time"],
                "cost": edge_data["cost"],
                "transfers": edge_data["transfers"]
            })

            total_cost += edge_data["cost"]
            total_time += edge_data["time"]
            total_transfers += edge_data["transfers"]
            total_distance += edge_data["weight"]

        return details, total_cost, total_time, total_transfers, total_distance