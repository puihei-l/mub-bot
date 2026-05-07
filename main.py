import os, discord
from discord.ext import commands
from dotenv import load_dotenv
from db.models import init_db

LEVELS = ["BEG1", "BEG2", "INT1", "INT2", "ADV", "COM"]

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def setup_hook():
    bot.db = await init_db("db/Coach.db")
    await bot.load_extension("cogs.bot")

    # Prefer guild sync (fast). Keep syncing minimal to avoid rate limits.
    if GUILD:
        guild_obj = discord.Object(id=int(GUILD))
        await bot.tree.sync(guild=guild_obj)
    else:
        await bot.tree.sync()

@bot.event
async def on_ready():
    print(f"Logged in - {bot.user} ({bot.user.id})")


bot.run(TOKEN)