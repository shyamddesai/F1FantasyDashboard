import sys
import requests
import os
import json
import hashlib
from urllib.parse import urlparse
from datetime import datetime
from tabulate import tabulate
import matplotlib.pyplot as plt

with open("cookie.json", "r", encoding="utf-8") as f:
    cookie_dict = json.load(f)
    cookie_dict = cookie_dict["Request Cookies"]

# Convert dict to properly formatted string for the cookie header
cookie_header = "; ".join([f"{key}={value}" for key, value in cookie_dict.items()])

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://fantasy.formula1.com",
    "Origin": "https://fantasy.formula1.com",
    "Cookie": cookie_header
}

with open("./players.json", "r", encoding="utf-8") as f:
    players = json.load(f)

# CACHE_DIR = "cache"
# os.makedirs(CACHE_DIR, exist_ok=True)

# def strip_meta_timestamps(data):
#     data = dict(data)  # shallow copy
#     data.pop("Meta", None)
#     data.pop("FeedTime", None)
#     return data

# def fetch_with_cache(url, headers=None):
#     # Identify category for subdirectory
#     parsed_url = urlparse(url)
#     path_parts = parsed_url.path.strip("/").split("/")
#     category = path_parts[1] if len(path_parts) > 1 else "misc"
#     sub_cache_dir = os.path.join(CACHE_DIR, category)
#     os.makedirs(sub_cache_dir, exist_ok=True)

#     # Cache key for base comparison
#     cache_key = hashlib.md5((url + json.dumps(headers or {}, sort_keys=True)).encode()).hexdigest()
#     base_cache_path = os.path.join(sub_cache_dir, f"{cache_key}.json")

#     # Fetch fresh data
#     response = requests.get(url, headers=headers)
#     response.raise_for_status()
#     new_data = response.json()

#     # Check existing cache
#     if os.path.exists(base_cache_path):
#         with open(base_cache_path, "r", encoding="utf-8") as f:
#             old_data = json.load(f)
#         if strip_meta_timestamps(old_data) == strip_meta_timestamps(new_data):
#             print(f"No meaningful change for {url}, cache not updated.")
#             return new_data

#     # Get timestamp from FeedTime or fallback to current UTC
#     try:
#         ts_str = new_data.get("FeedTime", {}).get("UTCTime") or new_data.get("Meta", {}).get("Timestamp", {}).get("UTCTime")
#         ts = datetime.strptime(ts_str, "%m/%d/%Y %I:%M:%S %p")
#     except:
#         ts = datetime.utcnow()

#     # Format timestamp
#     ts_filename = ts.strftime("%Y-%m-%dT%H-%M-%SZ")
#     versioned_path = os.path.join(sub_cache_dir, f"{cache_key}_{ts_filename}.json")

#     # Save both: latest pointer and timestamped snapshot
#     with open(versioned_path, "w", encoding="utf-8") as f:
#         json.dump(new_data, f, indent=2)
#     with open(base_cache_path, "w", encoding="utf-8") as f:
#         json.dump(new_data, f, indent=2)

#     print(f"Updated cache for {url} → {versioned_path}")
#     return new_data

# def clear_cache():
    # for file in os.listdir(CACHE_DIR):
    #     os.remove(os.path.join(CACHE_DIR, file))

# ================================

def build_player_team_url(uuid, userid, teamno=1, matchday=1):
    return f"https://fantasy.formula1.com/services/user/opponentteam/opponentgamedayplayerteamget/1/{uuid}-0-{userid}/{teamno}/{matchday}/1"
    
    # data = fetch_with_cache(
    #     f"https://fantasy.formula1.com/services/user/opponentteam/opponentgamedayplayerteamget/1/{uuid}-0-{userid}/{teamno}/{matchday}/1")
    # return data

def get_league_summary(players, headers, race_number, metric="Points", LL_DELTA=None):
    assert metric in ["Points", "Budget"], "Invalid metric. Use 'Points' or 'Budget'."
    
    metric_key = "gdpoints" if metric == "Points" else "maxteambal"
    location_map = extract_race_locations()
    RACE_DAYS = range(1, race_number + 1)
    table = []

    # Adjust header for LL delta
    total_label = "Total Points"
    if metric == "Points" and LL_DELTA is not None:
        total_label += " (LL Adjusted)"

    table_headers = ["Team Name", "Chips"] + [location_map.get(r, f"Race {r}") for r in RACE_DAYS]
    if metric == "Points":
        table_headers.append(total_label)

    for player in players:
        for team in player["teams"]:
            row = [team["name"]]
            metric_total = 0
            chips_value = "–"
            used_LL = False

            # Fetch latest available team data for chip summary
            latest_url = build_player_team_url(player["uuid"], player["userid"], team["teamno"], matchday=race_number)
            latest_response = requests.get(latest_url, headers=headers)

            if latest_response.status_code == 200:
                try:
                    latest_team_data = latest_response.json()['Data']['Value']['userTeam'][0]
                    chips_value = parse_chips(latest_team_data, race_number, cumulative=True)
                    used_LL = "LL" in chips_value
                except Exception:
                    chips_value = "⚠️"
            row.append(chips_value)

            for r in RACE_DAYS:
                url = build_player_team_url(player["uuid"], player["userid"], team["teamno"], matchday=r)
                response = requests.get(url, headers=headers)

                if response.status_code != 200:
                    row.append("❌")
                    continue

                try:
                    data = response.json()
                    team_data = data['Data']['Value']['userTeam'][0]

                    if metric == "Points":
                        value = team_data.get(metric_key)
                    elif metric == "Budget":
                        value = (
                            team_data.get(metric_key) or
                            team_data.get("maxTeambal") or
                            team_data.get("team_info", {}).get("maxTeambal")
                        )

                    if value is None:
                        row.append("⚠️")
                    else:
                        row.append(value)
                        if metric == "Points":
                            metric_total += value
                except Exception:
                    row.append("⚠️⚠️")

            if metric == "Points":
                if LL_DELTA is not None and not used_LL:
                    metric_total += LL_DELTA # Adjust for LL delta
                row.append(metric_total)
            table.append(row)

    table.sort(key=lambda x: x[-1] if isinstance(x[-1], (int, float)) else -1, reverse=True) # Sort by total points or budget

    colalign = ["left", "left"] + ["right"] * (len(table_headers) - 2)
    print(tabulate(table, headers=table_headers, tablefmt="grid", colalign=colalign))

def get_team_compositions(players, headers, race_number):
    table = []
    player_id_map = build_player_id_map()
    table_headers = ["Team Name", "Chips", "Driver 1", "Driver 2", "Driver 3", "Driver 4", "Driver 5", "Constructor 1", "Constructor 2"]

    for player in players:
        for team in player["teams"]:
            url = build_player_team_url(player["uuid"], player["userid"], team["teamno"], matchday=race_number)
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                row = [team["name"]] + ["❌"] * 7
                table.append(row)
                continue

            try:
                data = response.json()
                team_data = data["Data"]["Value"]["userTeam"][0]

                chip_info = parse_chips(team_data, race_number)
                player_ids = team_data["playerid"]

                drivers = []
                constructors = []

                for entry in sorted(player_ids, key=lambda x: x["playerpostion"]):
                    player_id = int(entry["id"])
                    name = player_id_map.get(player_id, f"Unknown ({player_id})")
                    if entry.get("iscaptain", 0):
                        name += " (2x)"
                    if entry.get("ismgcaptain", 0):
                        name += " (3x)"
                    pos = entry["playerpostion"]

                    if pos in range(1, 6):
                        drivers.append(name)
                    else:
                        constructors.append(name)

                # Pad if incomplete data
                while len(drivers) < 5:
                    drivers.append("⚠️")
                while len(constructors) < 2:
                    constructors.append("⚠️")

                row = [team["name"], chip_info] + drivers[:5] + constructors[:2]
                table.append(row)

            except Exception as e:
                print(f"Error parsing team for {team['name']}: {e}")
                row = [team["name"]] + ["⚠️"] * 7
                table.append(row)

    print(tabulate(table, headers=table_headers, tablefmt="grid"))

def parse_chips(team_data, race_number, cumulative=False):
    chips = []
    chip_mapping = {
        "limitlesstakengd": "LL",
        "is_wildcard_taken_gd_id": "WC",
        "finalfixtakengd": "FF",
        "nonigativetakengd": "NN",
        "extradrstakengd": "3x",
        "autopilottakengd": "AP"
    }

    for key, abbr in chip_mapping.items():
        value = team_data.get(key)
        
        if isinstance(value, (int, float, str)) and str(value).isdigit():
            value = int(value)
            if (cumulative and value <= race_number) or (not cumulative and value == race_number):
                chips.append((value, abbr))

    # Sort by race the chip was used
    chips.sort(key=lambda x: int(x[0]))

    return ", ".join([abbr for _, abbr in chips]) if chips else "–"

def season_summary(players, headers, race_number, include_all_teams=False):
    location_map = extract_race_locations()
    race_days = range(1, race_number + 1)
    team_points = {}

    for player in players:
        for team in player["teams"]:
            if not include_all_teams and team["teamno"] != 1:
                continue  # Skip T2 and T3s unless including all teams

            team_name = team["name"]
            team_points[team_name] = []
            cumulative = 0

            for r in race_days:
                url = build_player_team_url(player["uuid"], player["userid"], team["teamno"], matchday=r)
                response = requests.get(url, headers=headers)

                if response.status_code != 200:
                    team_points[team_name].append(cumulative)
                    continue

                try:
                    data = response.json()
                    value = data['Data']['Value']['userTeam'][0].get("gdpoints", 0)
                    if isinstance(value, (int, float)):
                        cumulative += value
                    team_points[team_name].append(cumulative)
                except:
                    team_points[team_name].append(cumulative)

    plt.figure(figsize=(24, 8))
    for team_name, points in team_points.items():
        line, = plt.plot(race_days, points, marker='o', linewidth=2, label=team_name)
        for i, score in enumerate(points):
            y_offset = -10 if i % 2 == 0 else 10
            plt.annotate(
                f"{int(score)}",
                (race_days[i], score),
                color=line.get_color(),
                fontsize=8,
                textcoords="offset points",
                clip_on=False,
                xytext=(0, y_offset),
                ha='center',
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7)
            )

    plt.xlabel("Circuit")
    plt.ylabel("Cumulative Points")
    plt.title("Cumulative Points per Race")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(race_days, [location_map.get(r, f"Race {r}") for r in race_days], rotation=45, ha='right')
    plt.legend(title="Teams", loc="upper left")
    plt.tight_layout()
    plt.show()

def cumulative_gap_from_leader(players, headers, race_number, include_all_teams=False):
    location_map = extract_race_locations()
    RACE_DAYS = range(1, race_number + 1)
    team_totals = {}

    for player in players:
        for team in player["teams"]:
            if not include_all_teams and team["teamno"] != 1:
                continue  # Skip T2 and T3s unless including all teams

            team_name = team["name"]
            cumulative_points = []
            total = 0

            for r in RACE_DAYS:
                url = build_player_team_url(player["uuid"], player["userid"], team["teamno"], matchday=r)
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    cumulative_points.append(total)
                    continue
                try:
                    data = response.json()
                    pts = data["Data"]["Value"]["userTeam"][0].get("gdpoints", 0)
                    total += pts
                    cumulative_points.append(total)
                except:
                    cumulative_points.append(total)

            team_totals[team_name] = cumulative_points

    # Normalize by subtracting the leader each round
    races = list(RACE_DAYS)
    all_teams = list(team_totals.keys())
    leader_per_race = [max(team_totals[team][i] for team in all_teams) for i in range(race_number)]

    plt.figure(figsize=(15, 9))
    for team, points in team_totals.items():
        gaps = [int(points[i] - leader_per_race[i]) for i in range(race_number)]
        line, = plt.plot(races, gaps, marker='o', linewidth=2, label=team)
        
        for i, gap in enumerate(gaps):
            if gap != 0:
                y_offset = -10 if i % 2 == 0 else 10
                plt.annotate(
                    f"{gap}",
                    (races[i], gap),
                    color=line.get_color(),
                    fontsize=8,
                    textcoords="offset points",
                    xytext=(0, y_offset),
                    clip_on=False,
                    ha='center',
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7)
                )

    plt.axhline(0, color="gray", linestyle="--", linewidth=1)
    plt.title("Cumulative Point Gap from Race Leader")
    plt.xlabel("Circuit")
    plt.ylabel("Points Behind Leader")
    plt.xticks(races, [location_map.get(r, f"Race {r}") for r in races], rotation=45, ha='right')
    plt.legend(title="Teams")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.show()

# ================================

def fetch_f1_data(RACE_NUMBER):
    FANTASY_API_URL = f"https://fantasy.formula1.com/feeds/drivers/{RACE_NUMBER}_en.json"

    response = requests.get(FANTASY_API_URL)
    if response.status_code == 200:
        return response.json()['Data']['Value']
    else:
        raise Exception("Failed to fetch data from Fantasy F1 API")

    # return fetch_with_cache(FANTASY_API_URL, headers=headers)['Data']['Value']

def get_driver_stats():
    data = fetch_f1_data(RACE_NUMBER)
    drivers = []
    entity_map = {}

    for item in data:
        if item.get("PositionName") == "DRIVER" and item.get("IsActive") == "1":
            full_name = item.get("FUllName")
            player_id = int(item["PlayerId"])
            entity_map[player_id] = full_name

            # Ignore None entries when missing data at the start of a race weekend
            additional_stats = item.get("AdditionalStats") or {}

            stats = {
                "Name": full_name,
                "Team": item.get("TeamName"),
                "Value (M)": float(item.get("Value", 0)),
                "Total Points": int(float(item.get("OverallPpints", 0))),
                "Position Points": int(additional_stats.get("total_position_pts", 0.0)),
                "DNF/DQ": int(additional_stats.get("total_dnf_dq_pts", 0.0)),
                "Overtaking": int(additional_stats.get("overtaking_pts", 0.0)),
                "Fastest Lap": int(additional_stats.get("fastest_lap_pts", 0.0)),
                "DotD": int(additional_stats.get("dotd_pts", 0.0)),
                "Value for Money": additional_stats.get("value_for_money", 0.0),
            }
            drivers.append(stats)

    return drivers, entity_map

def get_current_race_number():
    RACE_NUMBER_URL = "https://fantasy.formula1.com/feeds/limits/constraints.json"

    try:
        response = requests.get(RACE_NUMBER_URL)
        matchday_id = response.json()["Data"]["Value"]["GamedayId"]
        return matchday_id
    except Exception as e:
        print(f"⚠️ Could not fetch current race number: {e}")
        return None

def get_constructor_stats():
    data = fetch_f1_data(RACE_NUMBER)
    constructors = []
    entity_map = {}

    for item in data:
        if item.get("PositionName") == "CONSTRUCTOR" and item.get("IsActive") == "1":
            name = item.get("FUllName")
            player_id = int(item["PlayerId"])
            entity_map[player_id] = name

            stats = {
                "Name": name,
                "Value (M)": float(item.get("Value", 0)),
                "Total Points": int(float(item.get("OverallPpints", 0))),
                "Position Points": int(item["AdditionalStats"].get("total_position_pts", 0.0)),
                "DNF/DQ": int(item["AdditionalStats"].get("total_dnf_dq_pts", 0.0)),
                "Overtaking": int(item["AdditionalStats"].get("overtaking_pts", 0.0)),
                "Fastest Lap": int(item["AdditionalStats"].get("fastest_lap_pts", 0.0)),
                "Value for Money": item["AdditionalStats"].get("value_for_money", 0.0),
            }
            constructors.append(stats)

    return constructors, entity_map

def print_asset_table(assets):
    if not assets:
        print("No data to display.")
        return

    # Get headers
    headers = list(assets[0].keys())
    widths = [max(len(str(row[h])) for row in assets) for h in headers]
    widths = [max(w, len(h)) for w, h in zip(widths, headers)]

    # Print header
    print(" | ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("-+-".join("-" * w for w in widths))

    # Print rows
    for row in assets:
        print(" | ".join(str(row[h]).ljust(w) for h, w in zip(headers, widths)))

def print_driver_table():
    print("\n============ DRIVER STATS ============")
    drivers, _ = get_driver_stats()
    drivers = sorted(drivers, key=lambda x: x.get("Value (M)", 0), reverse=True)
    print_asset_table(drivers)

def print_constructor_table():
    print("\n============ CONSTRUCTOR STATS ============")
    constructors, _ = get_constructor_stats()
    constructors = sorted(constructors, key=lambda x: x.get("Value (M)", 0), reverse=True)
    print_asset_table(constructors)

def build_player_id_map():
    _, driver_map = get_driver_stats()
    _, constructor_map = get_constructor_stats()
    return {**driver_map, **constructor_map}

def extract_race_locations():
    F1_SCHEDULE_URL = f"https://fantasy.formula1.com/feeds/schedule/raceday_en.json"

    response = requests.get(F1_SCHEDULE_URL)
    response.raise_for_status()
    data = response.json()

    # data = fetch_with_cache(F1_SCHEDULE_URL, headers=headers)

    races = data.get("Data", {}).get("Value", [])
    circuit_dict = {}

    for event in races:
        race_number = event.get("MeetingNumber")
        circuit_location = event.get("CircuitLocation")

        if race_number and circuit_location:
            circuit_dict[race_number] = circuit_location

    # for race_number, location in circuit_dict.items():
    #     print(f"Race {race_number}: {location}")

    return circuit_dict

# ================================

if __name__ == "__main__":
    # ------ Race Number Configuration ------
    # By default, use the current race number from the API.
    # You can override via:
    #   1. Command-line argument: python f1_fantasy_dashboard.py 16
    #   2. Hardcoding: RACE_NUMBER = 16  # e.g., for Monza
    RACE_NUMBER = get_current_race_number()
    if len(sys.argv) > 1:
        try:
            RACE_NUMBER = int(sys.argv[1]) # Override race number from console argument
        except ValueError:
            print("Error: Race number must be an integer.")
            sys.exit(1)

    # Adjustment to estimate standings if everyone used LL chip
    LL_DELTA = 128 # Scuderia Sorpasso Jeddah LL Delta

    # TODO: Automate populating players.json given league ID

    # ------ Basic Summaries ------
    get_league_summary(players, headers, RACE_NUMBER)
    get_league_summary(players, headers, RACE_NUMBER, "Budget")

    # ------ Advanced Summaries ------
    # get_league_summary(players, headers, RACE_NUMBER, LL_DELTA=LL_DELTA) # LL adjusted points
    season_summary(players, headers, RACE_NUMBER, include_all_teams=True)
    cumulative_gap_from_leader(players, headers, RACE_NUMBER, include_all_teams=False)

    # ------ Team Lineups ------
    # get_team_compositions(players, headers, RACE_NUMBER-1) # Previous race
    # get_team_compositions(players, headers, RACE_NUMBER) # Current race

    # ------ Driver/Constructor Stats ------
    # print_driver_table()
    # print_constructor_table()
