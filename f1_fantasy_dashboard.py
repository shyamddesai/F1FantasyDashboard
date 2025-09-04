import os
import sys
import json
import requests
import matplotlib.pyplot as plt
from rich.console import Console
from rich.table import Table
from urllib.parse import unquote
from dotenv import load_dotenv

load_dotenv()
console = Console()

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

try:
    with open("./players.json", "r", encoding="utf-8") as f:
        players = json.load(f)
except (json.decoder.JSONDecodeError, FileNotFoundError):
    players = {}

# ================================

def fetch_league_players(player_uuid, league_id, save_path="players.json"):
    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        with open(save_path, "r", encoding="utf-8") as f:
            return json.load(f)
        
    if not player_uuid or not league_id:
        print(f"Invalid input: {player_uuid}, {league_id}")
        print("Provide a valid player UUID and league ID.")
        return
        
    LEAGUE_URL = f"https://fantasy.formula1.com/services/user/leaderboard/{player_uuid}/pvtleagueuserrankget/1/{league_id}/0/1/1/1000000/"

    resp = requests.get(LEAGUE_URL, headers=headers)

    data = resp.json()
    mem_ranks = data["Data"]["Value"]["memRank"]
    league_name = unquote(data["Data"]["Value"]["leagueInfo"]["leagueName"])

    league_players = {}

    for entry in mem_ranks:
        guid = entry["guid"]  # uuid-0-userid
        uuid = guid.split("-0-")[0]
        userid = guid.split("-0-")[-1]

        team_info = {
            "name": unquote(entry["teamName"]),
            "teamno": entry["teamNo"]
        }

        if uuid not in league_players:
            league_players[uuid] = {"uuid": uuid, "userid": userid, "teams": []}

        league_players[uuid]["teams"].append(team_info)

    players_list = list(league_players.values())

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(players_list, f, indent=2, separators=(',', ': '))

    print(f"Saved {len(players_list)} players from {league_name} to {save_path}")
    return players_list

def build_player_team_url(uuid, userid, teamno=1, matchday=1):
    return f"https://fantasy.formula1.com/services/user/opponentteam/opponentgamedayplayerteamget/1/{uuid}-0-{userid}/{teamno}/{matchday}/1"
    
    # data = fetch_with_cache(
    #     f"https://fantasy.formula1.com/services/user/opponentteam/opponentgamedayplayerteamget/1/{uuid}-0-{userid}/{teamno}/{matchday}/1")
    # return data

def get_league_summary(players, race_number, metric="Points", LL_DELTA=None, *, first=0, last=0, top=0):   
    if metric == "Points":
        all_days = list(range(1, race_number))
    elif metric == "Budget":
        all_days = list(range(1, race_number + 1))
    else:
        print("Invalid metric. Use 'Points' or 'Budget'.")
        return

    metric_key = "gdpoints" if metric == "Points" else "maxteambal"
    location_map = extract_race_locations()

    # Decide which races to show
    if first > 0 and last > 0:
        # Both flags: first N + last N
        days = all_days[:first] + all_days[-last:]
    elif first > 0:
        days = all_days[:first]
    elif last > 0:
        days = all_days[-last:]
    else:
        days = all_days

    rows, full_totals = [], []
    for player in players:
        for team in player["teams"]:
            chips = "–"
            used_LL = False

            # Fetch latest available team data for chip summary
            latest_url = build_player_team_url(player["uuid"], player["userid"], team["teamno"], matchday=race_number)
            latest_response = requests.get(latest_url, headers=headers)

            if latest_response.status_code == 200:
                try:
                    latest_team_data = latest_response.json()['Data']['Value']['userTeam'][0]
                    chips = parse_chips(latest_team_data, race_number, cumulative=True)
                    used_LL = "LL" in chips
                except Exception:
                    # chips = "⚠️"
                    pass

            race_vals = []
            for d in days:
                url = build_player_team_url(player["uuid"], player["userid"], team["teamno"], matchday=d)
                response = requests.get(url, headers=headers)
                val = None

                if response.status_code == 200:
                    try:
                        val = response.json()['Data']['Value']['userTeam'][0]
                        val = (
                            int(val["gdpoints"])
                            if metric == "Points"
                            else (val.get(metric_key) or
                                  val.get("maxTeambal") or
                                  val.get("team_info", {}).get("maxTeambal"))
                        )
                    except Exception:
                        val = "⚠️⚠️"
                        val = None
                race_vals.append(val if val is not None else "–")

            # Points total across all races
            total = 0
            for d_all in all_days:
                url = build_player_team_url(player["uuid"], player["userid"], team["teamno"], d_all)
                r_all = requests.get(url, headers=headers)
                if r_all.status_code == 200:
                    try:
                        total += int(r_all.json()['Data']['Value']['userTeam'][0]["gdpoints"])
                    except:
                        pass

            if metric == "Points" and LL_DELTA is not None and not used_LL:
                total += LL_DELTA # Adjust for LL delta

            rows.append([team["name"], chips] + race_vals + ([total] if metric == "Points" else []))
            full_totals.append(total)  

    rows = [r for _, r in sorted(zip(full_totals, rows), key=lambda x: x[0], reverse=True)] # Sort by total points or budget

    if top > 0:
        rows = rows[:top]

    cols = ["Team Name", "Chips"] + [location_map.get(d, f"R{d}") for d in days]
    if metric == "Points":
        cols.append("Total Points" if LL_DELTA is None else "Total Points (LL Adj.)")

    return print_rich_table(cols, rows)

def get_team_compositions(players, race_number):
    player_id_map = build_player_id_map()
    table_headers = ["Team Name", "Chips", "Driver 1", "Driver 2", "Driver 3", "Driver 4", "Driver 5", "Constructor 1", "Constructor 2"]

    rows = []
    for player in players:
        for team in player["teams"]:
            url = build_player_team_url(player["uuid"], player["userid"], team["teamno"], matchday=race_number)
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                row = [team["name"]] + ["❌"] * 7
            else:
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

                except Exception as e:
                    print(f"Error parsing team for {team['name']}: {e}")
                    row = [team["name"]] + ["⚠️"] * 7
            rows.append(row)

    race_location = extract_race_locations().get(race_number, f"Race {race_number}")
    return print_rich_table(table_headers, rows, title=f"Team Compositions for {race_location}")

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

def season_summary(players, race_number, include_all_teams=False):
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
    plt.gcf().canvas.manager.set_window_title("Cumulative Fantasy Points")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(race_days, [location_map.get(r, f"Race {r}") for r in race_days], rotation=45, ha='right')
    plt.legend(title="Teams", loc="upper left")
    plt.tight_layout()
    plt.show()

def cumulative_gap_from_leader(players, race_number, include_all_teams=False):
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
    plt.gcf().canvas.manager.set_window_title("Points Gap from Leader")
    plt.xlabel("Circuit")
    plt.ylabel("Points Behind Leader")
    plt.xticks(races, [location_map.get(r, f"Race {r}") for r in races], rotation=45, ha='right')
    plt.legend(title="Teams")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.show()

def cumulative_gap_from_leader_budget(players, race_number, include_all_teams=False):
    location_map = extract_race_locations()
    RACE_DAYS = range(1, race_number + 1)
    team_budgets = {}

    for player in players:
        for team in player["teams"]:
            if not include_all_teams and team["teamno"] != 1:
                continue

            team_name = team["name"]
            budgets = []
            for r in RACE_DAYS:
                url = build_player_team_url(player["uuid"], player["userid"], team["teamno"], matchday=r)
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    budgets.append(0 if not budgets else budgets[-1])
                    continue
                try:
                    data = response.json()
                    val = (
                        data["Data"]["Value"]["userTeam"][0].get("maxteambal") or
                        data["Data"]["Value"]["userTeam"][0].get("team_info", {}).get("maxTeambal") or
                        0
                    )
                    budgets.append(float(val))
                except Exception:
                    budgets.append(0 if not budgets else budgets[-1])
            team_budgets[team_name] = budgets

    # Compute budget gap to leader for each race
    all_teams = list(team_budgets.keys())
    budget_leader = [max([team_budgets[team][i] for team in all_teams]) for i in range(race_number)]

    plt.figure(figsize=(15, 9))
    races = list(RACE_DAYS)
    for team, budgets in team_budgets.items():
        gaps = [round(budgets[i] - budget_leader[i], 2) for i in range(race_number)]
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
    plt.title("Budget Gap from Leader per Race")
    plt.gcf().canvas.manager.set_window_title("Budget Gap from Leader")
    plt.xlabel("Circuit")
    plt.ylabel("Budget Behind Leader (Million)")
    plt.xticks(races, [location_map.get(r, f"Race {r}") for r in races], rotation=45, ha='right')
    plt.legend(title="Teams")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.show()

def budget_performance_by_race(players, race_number):
    location_map = extract_race_locations()
    RACE_DAYS = list(range(1, race_number + 1))
    team_deltas = {}

    for player in players:
        for team in player["teams"]:
            team_name = team["name"]
            vals = []

            for r in RACE_DAYS:
                url = build_player_team_url(player["uuid"], player["userid"], team["teamno"], matchday=r)
                response = requests.get(url, headers=headers)

                if response.status_code != 200:
                    vals.append(0 if not vals else vals[-1])
                    continue

                try:
                    data = response.json()
                    val = float(
                        data["Data"]["Value"]["userTeam"][0].get("maxteambal")
                        or data["Data"]["Value"]["userTeam"][0].get("team_info", {}).get("maxTeambal")
                        or 0
                    )
                    vals.append(val)

                except Exception:
                    vals.append(0 if not vals else vals[-1])
            vals = [v - 100 for v in vals]  # Normalize from 100 (starting budget)
            deltas = [vals[0]] + [vals[i] - vals[i-1] for i in range(1, len(vals))]
            team_deltas[team_name] = (deltas, team["teamno"])

    plt.figure(figsize=(24, 8))
    races = list(RACE_DAYS)
    for team, (deltas, _) in team_deltas.items():
        x = list(range(1, len(deltas) + 1))
        plt.plot(x, deltas, marker='o', linewidth=2, label=team)
        for i, delta in enumerate(deltas):
            if abs(delta) > 0:
                y_offset = -10 if i % 2 == 0 else 10
                plt.annotate(
                    f"{delta:+.1f}",
                    (x[i], deltas[i]),
                    fontsize=8,
                    color="black",
                    textcoords="offset points",
                    xytext=(0, y_offset),
                    ha='center',
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7)
                )

    plt.title(f"Race-by-Race Budget Performance Delta per Team")
    plt.xlabel("Circuit")
    plt.ylabel(f"Change in Budget")
    plt.xticks(races, [location_map.get(r, f"Race {r}") for r in races], rotation=45, ha='right')
    plt.legend(title="Teams")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.gcf().canvas.manager.set_window_title(f"Budget Performance Over Season")
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

def print_asset_table(assets, title):
    if not assets:
        print("No data to display.")
        return

    table_headers = list(assets[0].keys())
    rows = [[row[h] for h in table_headers] for row in assets]
    return print_rich_table(table_headers, rows, title=title)

def print_driver_table():
    drivers, _ = get_driver_stats()
    drivers = sorted(drivers, key=lambda x: x.get("Value (M)", 0), reverse=True)
    print_asset_table(drivers, title="Driver Stats")

def print_constructor_table():
    constructors, _ = get_constructor_stats()
    constructors = sorted(constructors, key=lambda x: x.get("Value (M)", 0), reverse=True)
    print_asset_table(constructors, title="Constructor Stats")

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

def print_rich_table(headers, rows, title=None, highlight=True, show_lines=True):
    table = Table(title=title, highlight=highlight, show_lines=show_lines)
    for idx, col in enumerate(headers):
        justify = "left" if idx < 2 else "right"
        table.add_column(col, justify=justify)
    for row in rows:
        table.add_row(*map(str, row))
    console.print(table)

# ================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            RACE_NUMBER = int(sys.argv[1]) # Override race number from console argument
        except ValueError:
            print("Error: Race number must be an integer.")
            sys.exit(1)

    # ================================
    # 🎯 Race Configuration
    # ================================
    # By default, use the current race number from the Fantasy F1 API
    # You can override via:
    #   1. Command-line argument: python f1_fantasy_dashboard.py 16
    #   2. Hardcoding: RACE_NUMBER = 16  # e.g., for Monza
    RACE_NUMBER = get_current_race_number()

    # Add a fixed points delta as if every manager had used LL
    LL_DELTA = 128

    # ================================
    # 🏎️ Fetch League Players
    # ================================
    # Automatically pulls all participants and their team entries
    # Requires your player UUID + league ID from F1 Fantasy website
    players = fetch_league_players(
        player_uuid=os.getenv("PLAYER_UUID"),
        league_id=os.getenv("PLAYER_LEAGUE")
    )

    # ================================
    # 📊 Basic League Summaries
    # ================================
    # get_league_summary(players, RACE_NUMBER)
    # get_league_summary(players, RACE_NUMBER, "Budget")
    
    get_league_summary(players, RACE_NUMBER, last=5)
    get_league_summary(players, RACE_NUMBER, "Budget", last=5)
    
    # ================================
    # 🔍 Advanced Summaries
    # ================================
    # get_league_summary(players, RACE_NUMBER, LL_DELTA=LL_DELTA)   # LL-adjusted points
    # season_summary(players, RACE_NUMBER, include_all_teams=True)  # Season progression
    cumulative_gap_from_leader(players, RACE_NUMBER)              # Points gap vs leader
    # cumulative_gap_from_leader_budget(players, RACE_NUMBER)       # Budget gap vs leader
    budget_performance_by_race(players, RACE_NUMBER)              # Budget performance by race

    # ================================
    # 🧑‍🤝‍🧑 Team Lineups
    # ================================
    # get_team_compositions(players, RACE_NUMBER - 1)  # Previous race
    # get_team_compositions(players, RACE_NUMBER)      # Current race
    
    # ================================
    # 📈 Driver/Constructor Asset Stats
    # ================================
    # print_driver_table()
    # print_constructor_table()