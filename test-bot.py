import os, discord, asyncio, sqlite3
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Help - Commands", color=discord.Color.blue())
    for command in bot.commands:
        embed.add_field(name=f"!{command.name}", value=command.help or "No description", inline=False)
    await ctx.send(embed=embed)

@bot.command(help="Swap Shifts")
async def swap(ctx):
    await ctx.send(f'Which shift would you like to swap?')


bot.run(TOKEN)