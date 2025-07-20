import os, discord, asyncio, aiosqlite
from discord.ext import commands
from dotenv import load_dotenv

LEVELS = ["BEG1", "BEG2", "INT1", "INT2", "ADV", "COM"]

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    bot.db = await aiosqlite.connect('Coach.db')

    c = await bot.db.cursor()
    await c.execute("""CREATE TABLE IF NOT EXISTS Coaches(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
                    )""")
    await c.execute("""CREATE TABLE IF NOT EXISTS Classes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    week INTEGER,
                    day INTEGER
                    )""")
    await c.execute("""CREATE TABLE IF NOT EXISTS CoachClasses(
                    class_id INTEGER,
                    coach_id INTEGER,
                    PRIMARY KEY (class_id, coach_id),
                    FOREIGN KEY (class_id) REFERENCES Classes(id),
                    FOREIGN KEY (coach_id) REFERENCES Coaches(id)
                    )""")
    
    # Semester plan (12 weeks, 192 classes in total)
    row = await c.execute("SELECT 1 FROM Classes LIMIT 1;")
    result = await row.fetchone()
    print(result is None)
    if result is None:
        for i in range(1,13):
            for j in range(0,4):
                for k in range(1,7,2):
                    await c.execute("""INSERT INTO Classes (level, week, day)
                                    VALUES (?,?,?);""",
                                    (LEVELS[j], i, k, ))
            for j in range(4,6):
                for k in range(2,6,2):
                    await c.execute("""INSERT INTO Classes (level, week, day)
                                    VALUES (?,?,?);""",
                                    (LEVELS[j], i, k, ))
    await bot.db.commit()

    await bot.load_extension('cogs.bot')
    print(f"Logged in - {bot.user} ({bot.user.id})")


bot.run(TOKEN)