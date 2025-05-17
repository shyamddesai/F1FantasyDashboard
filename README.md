# F1 Fantasy League Dashboard
A Python script for summarizing your Formula 1 Fantasy league standings, team performance, and fair comparisons using chip usage adjustments.

## Features
* Fetch team performance by race and totals
* Identify chip usage (e.g., Limitless, Wildcard)
* Adjust for unused Limitless chip ("LL Delta") to compare standings fairly
* Customize for budget or points tracking

---

## Getting Started
### 1. Clone the repository

```bash
git clone https://github.com/shyamddesai/f1-fantasy-dashboard.git
cd f1-fantasy-dashboard
```

### 2. Create the required files
#### `cookie.json`
Stores your session cookies so the script can make authenticated requests.
The JSON structure should match what you get when copying cookies from your browser's developer tools.

```json
{
  "Request Cookies": {
    "entitlement_token": "...",
    "F1_FANTASY_007": "...",
    "login-session": "...",
    ...
  }
}
```
You can obtain these by logging into [https://fantasy.formula1.com](https://fantasy.formula1.com), opening Developer Tools (F12), inspecting any API requests under the **Network** tab, and copying the request cookies.

#### `players.json`
Holds your league player/team configuration. Each player entry includes their F1 Fantasy uuid, userid, and a list of team objects (each with name and teamno).
```json
[
  {
    "uuid": "abc123...",
    "userid": "123456",
    "teams": [
      {"name": "Scuderia Sorpasso", "teamno": 1},
      {"name": "Mercedes Wunderwaffe", "teamno": 2}
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
You can find the `uuid`, `userid`, and `teamno` values using your browser developer tools while inspecting your fantasy teams.

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
Modify the following values at the bottom of the script to control output:
```python
RACE_NUMBER = 6  # The race number to summarize stats up to.
                 # Example: Set to 6 for data upto the Miami GP 2025.

LL_DELTA = 128   # Points gained from using the Limitless chip.
                 # Used to estimate standings if everyone used LL, either perfectly or sub-optimally.
```

At the moment, to switch between the different available outputs, you'll need to comment or uncomment the relevant function calls in the script:
```python
# Print current driver and constructor statistics
print_driver_table()
print_constructor_table()

# Show league standings
get_league_summary(players, headers, RACE_NUMBER)
get_league_summary(players, headers, RACE_NUMBER, LL_DELTA=LL_DELTA)  # With Limitless adjustment
get_league_summary(players, headers, RACE_NUMBER, "Budget")  # Show budget rankings

# Show team lineups
get_team_compositions(players, headers, RACE_NUMBER)

# Season overview
season_summary(players, headers, RACE_NUMBER, include_all_teams=True)
cumulative_gap_from_leader(players, headers, RACE_NUMBER, include_all_teams=False)
```

---

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

---

## Coming Soon
* Automatically fetch the current/latest race number from the API
* Auto-populate `players.json` using your league ID
* Build a simple console-based UI to choose actions (instead of commenting/uncommenting functions)
* Add command-line arguments for common operations (e.g. `--summary`, `--budget`, `--ll-adjust`)
* Add request/result caching to avoid redundant API calls and improve performance
