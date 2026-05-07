import aiosqlite

LEVELS = ["BEG1", "BEG2", "INT1", "INT2", "ADV", "COM"]
DAY_CODES = ["MON", "TUE", "WED", "THU", "FRI"]

async def init_db(db_path):
    db = await aiosqlite.connect(db_path)
    c = await db.cursor()

    await c.execute("""CREATE TABLE IF NOT EXISTS Coaches(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
                    )""")
    # Optional identity mapping so we can require approvals.
    # These ALTERs are safe to run repeatedly (we guard via PRAGMA below).
    cols_cur = await c.execute("PRAGMA table_info(Coaches);")
    cols = await cols_cur.fetchall()
    existing = {row[1] for row in cols}
    if "discord_user_id" not in existing:
        await c.execute("ALTER TABLE Coaches ADD COLUMN discord_user_id INTEGER;")
    if "guild_id" not in existing:
        await c.execute("ALTER TABLE Coaches ADD COLUMN guild_id INTEGER;")
    await c.execute("""CREATE TABLE IF NOT EXISTS Classes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    week INTEGER,
                    day TEXT
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
    if result is None:
        for i in range(1,13):
            for j in range(0,4):
                for k in (0, 2, 4):
                    await c.execute("""INSERT INTO Classes (level, week, day)
                                    VALUES (?,?,?);""",
                                    (LEVELS[j], i, DAY_CODES[k], ))
            for j in range(4,6):
                for k in (1, 3):
                    await c.execute("""INSERT INTO Classes (level, week, day)
                                    VALUES (?,?,?);""",
                                    (LEVELS[j], i, DAY_CODES[k], ))
    await db.commit()
    return db
