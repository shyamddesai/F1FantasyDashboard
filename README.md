# F1 Fantasy League Dashboard
A Python dashboard for summarizing your Formula 1 Fantasy league standings, team performance, and making fair comparisons with chip usage adjustments.

## Features
* Fetches your league players & their teams from F1 Fantasy
* Identifies chip usage (Limitless, Wildcard, Final Fix, etc.)
* Adjust for unused Limitless chip ("LL Delta") simulate scenarios where all teams used it
* Compare team lineups, drivers, and constructors for each race
* Visualize cumulative points & points gap vs leader across the season

---

## Getting Started
### 1. Clone the repository

```bash
git clone https://github.com/shyamddesai/F1FantasyDashboard.git
cd F1FantasyDashboard
```

### 2. Create the required files
#### `cookie.json`
Store your session cookies so the script can authenticate requests to the F1 Fantasy API.

How to obtain the request cookie:
1. Log in to [https://fantasy.formula1.com](https://fantasy.formula1.com)
2. Go to "My Team" or open any of your Private Leagues.
3. Press F12 (open Developer Tools) → click the Network tab.
4. In the search/filter box, type `raceday` to find a request like raceday_en.json 
> Any JSON API request works, but raceday is an easy one to spot
5. Click that request → go to the Cookies tab → Right‑click → Copy All cookies.
6. Paste everything into cookie.json.


```json
{
  "Request Cookies": {
    "consentDate": "...",
    "consentUUID": "..."
    "F1_FANTASY_007": "...",
    ...
    "login-session": "...",
    "reese84": "..."
  }
}
```
The JSON structure should match exactly what you get when copying cookies from your browser’s developer tools.

⚠️ Note: Cookies expire. If API calls start failing, you need to repeat the steps above and refresh your cookie.json.


#### `.env`
Contains your UUID and League ID so the script can auto‑fetch all players.
1. In DevTools (still on the Network tab), filter by league.
2. Find a request URL that looks like this:
```
/services/user/leaderboard/abcdef12-3456-7890-abcd-ef1234567890/pvtleagueuserrankget/1/1234567/0/1/1/10/
```
3. From that URL:
- abcdef12-3456-7890-abcd-ef1234567890 → this is your PLAYER_UUID
- 1234567 → this is your LEAGUE_ID
4. Put them into .env:
```
PLAYER_UUID=abcdef12-3456-7890-abcd-ef1234567890
PLAYER_LEAGUE=1234567
```


#### `players.json`
This file is automatically populated on first run using your .env. 
Each entry links a UUID → user ID → list of fantasy teams.

(Optional) If you want to include an extra team (for example, one of your second/third teams outside the league), you can add it manually. Just add "name" and "teamno" to the "teams" list for yourself:
```json
[
  {
    "uuid": "abc123...",
    "userid": "123456",
    "teams": [
      {"name": "Scuderia Sorpasso", "teamno": 1},
      {"name": "Mercedes Wunderwaffe", "teamno": 2} // Adding this team
    ]
  },
  {
    "uuid": "xyz789...",
    "userid": "789012",
    "teams": [
      {"name": "Redline Rockets", "teamno": 1}
    ]
  }
]
```
This is useful if you want to include a personal secondary team for comparison.

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Script
```bash
python f1_fantasy_dashboard.py
```

### Configuration Variables
You can configure core behavior at the bottom of the script:
```python
RACE_NUMBER = 6  # The race number to summarize stats up to.
                 # Default: Fetch current race from the API
                 # You can rewrite it to 6 for data upto the Miami GP 2025.

LL_DELTA = 128   # Points gained from using the Limitless chip.
                 # Add points to simulate balanced LL usage, either perfectly or sub-optimally.
```

At the moment, outputs are toggled by commenting / uncommenting function calls:
```python
# League Standings
get_league_summary(players, headers, RACE_NUMBER)
get_league_summary(players, headers, RACE_NUMBER, "Budget")
get_league_summary(players, headers, RACE_NUMBER, LL_DELTA=LL_DELTA) # LL-adjusted points

# Team Lineups
get_team_compositions(players, headers, RACE_NUMBER - 1)  # Previous race
get_team_compositions(players, headers, RACE_NUMBER)      # Current race

# Season Overview
season_summary(players, headers, RACE_NUMBER, include_all_teams=True)               # Season progression
cumulative_gap_from_leader(players, headers, RACE_NUMBER, include_all_teams=False)  # Points gap vs leader

# Driver/Constructor Asset Statistics
print_driver_table()
print_constructor_table()
```

---

## League Summary
### Points Summary (default)
```python
get_league_summary(players, headers, RACE_NUMBER)
```
Displays each team's total fantasy points per race.
![Points Summary](https://github.com/user-attachments/assets/80d520c8-8d6b-4366-bd7a-6c8047047441)

### Budget Summary
```python
get_league_summary(players, headers, RACE_NUMBER, "Budget")
```
Displays each team’s budget across the season.
![Budget Summary](https://github.com/user-attachments/assets/01a33d1e-3786-48da-99b3-8cf0c45a02cd)

### Adjusted Points Summary
```python
get_league_summary(players, headers, RACE_NUMBER, LL_DELTA=LL_DELTA)
```
Simulates how total standings might look if every remaining team uses the Limitless chip optimally or sub-optimally.
![LL Adjusted](https://github.com/user-attachments/assets/07313f82-c315-4cb2-92fa-e9055f50629d)

---

## League Team Compositions
```python
get_team_compositions(players, headers, RACE_NUMBER)
```
Show each team's full lineup for a given race.
![Team Compositions](https://github.com/user-attachments/assets/6bb5d01a-0e0c-4405-8cb1-4b19a7860db2)

---

## Season Summary
### Cumulative Points
```python
season_summary(players, headers, RACE_NUMBER, include_all_teams=True)
```
Track how each team accumulates points across the season.
![Cumulative Points](https://github.com/user-attachments/assets/3fcb5bde-84dc-411b-b62d-efc5709af851)

### Cumulative Gap to Leader
```python
cumulative_gap_from_leader(players, headers, RACE_NUMBER, include_all_teams=False)
```
Show how far each team is from the league leader at each race. Helps identify which weekends were pivotal turning points.
![Gap to Leader](https://github.com/user-attachments/assets/ce33696c-5ea8-486f-80c2-6f6a1d1d9c3e)

## Fantasy Statistics
### Driver Statistics
```python
print_driver_table()
```
![Driver Table](https://github.com/user-attachments/assets/5c2604cc-6cf9-42e1-ac1c-9fa22046b261)

### Constructor Statistics
```python
print_constructor_table()
```
![Constructor Table](https://github.com/user-attachments/assets/f8718dea-ca9b-46b2-9fe4-6305b7a14caa)


---

## Coming Soon
* Interactive console-based UI to choose actions (instead of commenting/uncommenting functions)
* Add command-line arguments for common operations (e.g. `--summary`, `--budget`, `--ll-adjust`)
* Add request/result caching to avoid redundant API calls and improve performance
* Export tables to CSV/Excel for deeper analysis