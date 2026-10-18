import json
import urllib.request
from datetime import date, timedelta

BASE_URL = "http://localhost:8000/api/v1"

def http_post(endpoint, payload=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def http_get(endpoint, token=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def run_test():
    print("=== STARTING FULL END-TO-END FLOW TEST ===")

    # 1. Login as Motorista
    print("\n1. Logging in as Motorista...")
    driver_login = http_post("/auth/login", {
        "email": "motorista@longbeach.com",
        "password": "driver123"
    })
    driver_token = driver_login["access_token"]
    print(f"Driver logged in: {driver_login['full_name']} (Role: {driver_login['role']})")

    # 2. Motorista creates a Trip with 3 Final Destinations (Faculdade A, B, C)
    print("\n2. Motorista creating Trip with 3 final destinations...")
    trip_payload = {
        "name": "Rota Universitária Manhã - Região Central/Oeste",
        "shift": "MORNING",
        "origin_address": "Garagem Central - Av. Rebouças, 1500",
        "origin_latitude": -23.5670,
        "origin_longitude": -46.6800,
        "is_active": True,
        "destinations": [
            {
                "destination_name": "Faculdade A - USP Butantã",
                "address": "Av. Prof. Luciano Gualberto, 300",
                "latitude": -23.5580,
                "longitude": -46.7315,
                "drop_order": 1
            },
            {
                "destination_name": "Faculdade B - Mackenzie Higienópolis",
                "address": "Rua da Consolação, 930",
                "latitude": -23.5482,
                "longitude": -46.6521,
                "drop_order": 2
            },
            {
                "destination_name": "Faculdade C - São Judas Mooca",
                "address": "Rua Taquari, 546",
                "latitude": -23.5505,
                "longitude": -46.5985,
                "drop_order": 3
            }
        ]
    }
    trip = http_post("/trips", trip_payload, token=driver_token)
    trip_id = trip["id"]
    print(f"Trip created: '{trip['name']}' (ID: {trip_id}) with {len(trip['destinations'])} destinations.")

    # 3. Motorista onboards a NEW Client (Lucas Estudante) and attaches him to the trip
    print("\n3. Motorista registering a new client directly...")
    new_client_payload = {
        "email": f"lucas_{date.today().isoformat()}@longbeach.com",
        "password": "lucaspassword123",
        "full_name": "Lucas Estudante",
        "phone": "(11) 95555-4444",
        "pickup_address": "Rua Oscar Freire, 800 - Jardins, SP",
        "pickup_latitude": -23.5620,
        "pickup_longitude": -46.6690,
        "destination_address": "Faculdade A - USP",
        "trip_assignments": [
            {
                "trip_id": trip_id,
                "days_of_week": ["MONDAY", "WEDNESDAY", "FRIDAY"]
            }
        ]
    }
    lucas_client = http_post("/drivers/register-client", new_client_payload, token=driver_token)
    print(f"New client registered and linked: {lucas_client['user']['full_name']} (ID: {lucas_client['id']})")

    # 4. Attach existing client (Maria Estudante) to the trip as well
    print("\n4. Attaching existing client (Maria Estudante) to the trip...")
    maria_login = http_post("/auth/login", {
        "email": "cliente@longbeach.com",
        "password": "client123"
    })
    maria_token = maria_login["access_token"]
    maria_client_id = maria_login["client_id"]

    http_post(f"/trips/{trip_id}/clients", {
        "client_id": maria_client_id,
        "days_of_week": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
    }, token=driver_token)
    print(f"Maria Estudante attached to trip.")

    # 5. Daily Attendance Confirmation
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    print(f"\n5. Registering attendance for tomorrow ({tomorrow})...")

    # Maria CONFIRMS she is going
    maria_att = http_post(f"/trips/{trip_id}/attendance?trip_date={tomorrow}", {
        "status": "CONFIRMED",
        "notes": "Estarei na calçada às 06:40 pontual!"
    }, token=maria_token)
    print(f"Maria attendance submitted: {maria_att['status']} (Notes: '{maria_att['notes']}')")

    # Lucas logs in and marks ABSENT ("Hoje faltei")
    lucas_login = http_post("/auth/login", {
        "email": new_client_payload["email"],
        "password": new_client_payload["password"]
    })
    lucas_token = lucas_login["access_token"]

    lucas_att = http_post(f"/trips/{trip_id}/attendance?trip_date={tomorrow}", {
        "status": "ABSENT",
        "notes": "Médico pela manhã, não vou hoje."
    }, token=lucas_token)
    print(f"Lucas attendance submitted: {lucas_att['status']} (Notes: '{lucas_att['notes']}')")

    # 6. Motorista calculates route for tomorrow (ONLY confirmed passengers)
    print(f"\n6. Motorista calculating route for {tomorrow}...")
    calc_res = http_post(f"/trips/{trip_id}/calculate-route?trip_date={tomorrow}", None, token=driver_token)

    print("\n=== ROUTE CALCULATION RESULT ===")
    print(f"Trip: {calc_res['trip_name']}")
    print(f"Date: {calc_res['trip_date']}")
    print(f"Provider: {calc_res['provider']}")
    print(f"Confirmed Passengers Count: {calc_res['confirmed_passengers_count']}")
    print(f"Total Distance: {calc_res['total_distance_km']} km")
    print(f"Total Estimated Duration: {calc_res['total_duration_minutes']} min")
    print("\nStops Sequence:")
    for stop in calc_res["stops"]:
        stop_type = stop["stop_type"]
        name = stop["name"]
        eta = stop["estimated_arrival_minutes"]
        print(f"  [{stop['stop_order']}] ({stop_type}) - {name} | ETA: +{eta} min | Addr: {stop['address']}")

    # Validation assertions
    assert calc_res["confirmed_passengers_count"] == 1, "Only Maria should be confirmed!"
    stop_names = [s["name"] for s in calc_res["stops"]]
    assert "Maria Estudante" in stop_names, "Maria should be in stops!"
    assert "Lucas Estudante" not in stop_names, "Lucas (absent) must NOT be in stops!"
    assert "Faculdade A - USP Butantã" in stop_names, "Faculdade A must be in destinations!"
    assert "Faculdade B - Mackenzie Higienópolis" in stop_names, "Faculdade B must be in destinations!"
    assert "Faculdade C - São Judas Mooca" in stop_names, "Faculdade C must be in destinations!"

    print("\n✅ ALL ASSERTIONS PASSED! End-to-end multi-agent flow is 100% operational!")

if __name__ == "__main__":
    run_test()
