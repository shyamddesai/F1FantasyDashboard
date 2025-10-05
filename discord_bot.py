import os
import io
import re
import sys
import json
import pathlib
import discord
import matplotlib.pyplot as plt
import f1_fantasy_dashboard as f1fd
from requests.exceptions import JSONDecodeError
from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands
from dotenv import load_dotenv
from io import StringIO

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
PREFIX = "f1!"

intents = discord.Intents.default()
intents.message_content = True

prefixes = [PREFIX] + [f"<@1415422643091275798> ", f"<@!1415422643091275798> "]
bot = commands.Bot(command_prefix=prefixes, intents=intents)

async def fetch_players():
    cache = pathlib.Path("players.json")
    if cache.is_file() and cache.stat().st_size > 0:
        return json.loads(cache.read_text(encoding="utf-8"))

    try:
        players = f1fd.fetch_league_players()
    except JSONDecodeError:
        print("[red]🍪  Session expired – re-harvesting cookies…[/red]")
        f1fd.harvest_f1_cookies(force=True)
        players = f1fd.fetch_league_players()
    return players

def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def ascii_table_to_image(table_text, font_path="DejaVuSansMono.ttf", font_size=14, padding=10):
    lines = table_text.split('\n')
    font = ImageFont.truetype(font_path, font_size)

    # Calculate image size
    max_line_width = 0
    total_height = 0
    line_heights = []

    for line in lines:
        bbox = font.getbbox(line)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        line_heights.append(height)
        if width > max_line_width:
            max_line_width = width
        total_height += height

    img_width = max_line_width + 2 * padding
    img_height = total_height + 2 * padding

    image = Image.new('RGB', (img_width, img_height), 'white')
    draw = ImageDraw.Draw(image)

    y = padding
    for i, line in enumerate(lines):
        draw.text((padding, y), line, font=font, fill='black')
        y += line_heights[i]

    buf = io.BytesIO()
    image.save(buf, format='PNG')
    buf.seek(0)
    return buf

@bot.event
async def on_ready():
    f1fd.harvest_f1_cookies()
    print(f"{bot.user} connected to Discord!")
    print(f"Prefixes: {prefixes}")

class Help(commands.DefaultHelpCommand):
    def get_ending_note(self):
        return ""

    def format_bot_help(self, mapping):
        out = ["F1 Fantasy Bot Commands"]
        for cog, cmds in mapping.items():
            for c in cmds:
                out.append(f"{self.context.clean_prefix}{c.name}")
                out.append(c.description or "")
        return "\n".join(out)

bot.help_command = Help(
    commands_heading="",
    no_category="Commands",
    dm_help=None
)

@bot.command(help ="Show budget performance graph over the season")
async def budget_performance(ctx, race_number: int = None):
    if race_number is None:
        race_number = f1fd.get_current_race_number()
    print(f"Generating budget performance visualization for race {race_number}...")

    players = await bot.loop.run_in_executor(None, fetch_players)
    fig = f1fd.budget_performance_by_race(players, race_number, show_plot=False)
    
    buf = io.BytesIO()
    fig.savefig(buf, format='PNG')
    buf.seek(0)
    plt.close()
    await ctx.send(file=discord.File(fp=buf, filename=f"budget_performance_{race_number}.png"))

@bot.command(help="Show points for the last N races")
async def points(ctx, race_number: int = None, last: int = 5):
    if not race_number:
        race_number = f1fd.get_current_race_number()
    print(f"Generating points summary for last {last} races...")

    players = await fetch_players()

    output = StringIO()
    sys.stdout = output
    f1fd.get_league_summary(players, race_number, metric="Points", last=last)
    sys.stdout = sys.__stdout__
    
    table_text = output.getvalue()
    print(table_text)

    ascii_text = strip_ansi_codes(table_text)
    points_table = ascii_table_to_image(ascii_text)

    await ctx.send(file=discord.File(fp=points_table, filename="points.png"))

@bot.command(help="Show budget for the last N races")
async def budget(ctx, race_number: int = None, last: int = 5):    
    if not race_number:
        race_number = f1fd.get_current_race_number()
    print(f"Generating budget summary for last {last} races...")

    players = await fetch_players()
    
    output = StringIO()
    sys.stdout = output
    f1fd.get_league_summary(players, race_number, metric="Budget", last=last)
    sys.stdout = sys.__stdout__
    
    table_text = output.getvalue()
    ascii_text = strip_ansi_codes(table_text)
    budget_table = ascii_table_to_image(ascii_text)
    await ctx.send(file=discord.File(fp=budget_table, filename="budget.png"))

@bot.command(help="Show team compositions for the race")
async def teams(ctx, race_number: int = None):
    if not race_number:
        race_number = f1fd.get_current_race_number()
    print(f"Generating team compositions for race {race_number}...")

    players = await fetch_players()

    output = StringIO()
    sys.stdout = output
    f1fd.get_team_compositions(players, race_number)
    sys.stdout = sys.__stdout__
    
    table_text = output.getvalue()
    ascii_text = strip_ansi_codes(table_text)
    teams_table = ascii_table_to_image(ascii_text)
    await ctx.send(file=discord.File(fp=teams_table, filename="teams.png"))

@bot.command(help="Show points progression over the season")
async def season(ctx, race_number: int = None):
    if not race_number:
        race_number = f1fd.get_current_race_number()
    print(f"Generating season summary visualization until race {race_number}...")

    players = await fetch_players()

    fig = f1fd.season_summary(players, race_number, include_all_teams=True, show_plot=False)
    buf = io.BytesIO()
    fig.savefig(buf, format='PNG')
    buf.seek(0)
    plt.close(fig)
    
    await ctx.send(file=discord.File(fp=buf, filename=f"season_summary_{race_number}.png"))

@bot.command(help="Show points gap from leader graph over the season")
async def gap_points(ctx, race_number: int = None):
    if not race_number:
        race_number = f1fd.get_current_race_number()
    print(f"Generating points gap from leader visualization until race {race_number}...")

    players = await fetch_players()

    fig = f1fd.cumulative_gap_from_leader(players, race_number, show_plot=False)
    buf = io.BytesIO()
    fig.savefig(buf, format='PNG')
    buf.seek(0)
    plt.close(fig)

    await ctx.send(file=discord.File(fp=buf, filename=f"gap_points_{race_number}.png"))

@bot.command(help="Show budget gap from leader graph over the season")
async def gap_budget(ctx, race_number: int = None):
    if not race_number:
        race_number = f1fd.get_current_race_number()
    print(f"Generating budget gap from leader visualization until race {race_number}...")
    
    players = await fetch_players()
    
    fig = f1fd.cumulative_gap_from_leader_budget(players, race_number, show_plot=False)
    buf = io.BytesIO()
    fig.savefig(buf, format='PNG')
    buf.seek(0)
    plt.close(fig)
    
    await ctx.send(file=discord.File(fp=buf, filename=f"gap_budget_{race_number}.png"))

if __name__ == "__main__":
    bot.run(TOKEN)