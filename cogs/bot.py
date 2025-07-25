import os, discord, asyncio, aiosqlite
from discord.ext import commands
from dotenv import load_dotenv
from tabulate import tabulate
from .ui.button import ConfirmView

load_dotenv()
SECRETARY = int(os.getenv('SECRETARY_ID'))
ADMIN = int(os.getenv('ADMIN_ID'))
WEEKS = 12

class BotCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx, optcmd = None):
    
        if optcmd is None:
            embed = discord.Embed(
                title="Help - Commands",
                color=discord.Color.blue()
            )
            embed.description = """Use !help [command] for more info on a command.
                                    You do not need the brackets."""
            for cmd in sorted(self.bot.commands, key=lambda c: c.name):
                if not cmd.hidden and cmd.name != "help":
                    short = getattr(cmd, "short_help", cmd.short_doc or "No description")
                    embed.add_field(name=f'!{cmd.name}', value=short, inline=False)
            await ctx.send(embed=embed)
        else:
            cmd = self.bot.get_command(optcmd)
            if cmd is None:
                await ctx.send(f'Command {optcmd} not found.')
            else:
                desc = cmd.help or "No description"
                embed = discord.Embed(
                    title=f"**Help for !{cmd.name}:**",
                    color=discord.Color.dark_purple()
                )
                embed.description = desc
                await ctx.send(embed=embed)

    @commands.command()
    async def assignm(self, ctx, coach, day, classLevel):
        """
        Used by Admin/Secretary only (Bulk assign classes to a coach)

        **Usage:**
            !assignm `coach` `day` `class level`
        
        **Example:**
            !assignm `lenin` `2` `com`
        
        """
        def check(msg):
            return msg.author.id == ADMIN and msg.channel == thread
        
        if not ctx.author.id == ADMIN:
            await ctx.send(f"You don't have permission to !assignm")
            return
        
        if (coach == None or day == None or classLevel == None):
            await thread.send(f"Use !help assignm for usage")
            return
        
        thread_name = f"Bulk assign classes - {ctx.author.display_name}"
        thread = await ctx.channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.public_thread,
            auto_archive_duration=1440
        )

        coach = coach.upper()
        day = day.upper()
        classLevel = classLevel.upper()

        async with aiosqlite.connect('Coach.db') as db:
            cursor = await db.execute("""SELECT id FROM Classes
                                        WHERE day = ?
                                        AND UPPER(level) = ?;""", (day, classLevel,))
            result = await cursor.fetchall()
            if result is None:
                await thread.send(f"No {classLevel} classes on day {day}.")
                return

            cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (coach,))
            id = await cursor.fetchone()
            if id is None:
                await thread.send(f"Coach {coach} is not found.")
                return
            
            coach_id = id[0]

            for row in result:
                class_id = row[0]
                await db.execute(f"""INSERT INTO CoachClasses (class_id, coach_id)
                                VALUES (?,?);""",
                                (class_id, coach_id,))
                await db.commit()
            await thread.send("All done")


    @commands.command()
    async def drop(self, ctx, coach = None, day = None, week = None, classLevel = None):
        """
        Drop shift

        **Usage:**
            !drop `coach` `day` `week` `class level`
        
        **Example:**
            !drop `lenin` `2` `12` `com`
        """

        def check(msg):
            return msg.author.id == ADMIN and msg.channel == thread
        
        thread_name = f"Drop Request - {ctx.author.display_name}"
        thread = await ctx.channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.public_thread,
            auto_archive_duration=1440
        )
        try:
            if coach is None:
                await thread.send(f'Coach name?')
                coach_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if coach_msg is None:
                    await thread.send("No input. Request cancelled")
                    return
                coach = coach_msg.content.strip()
            if day is None:
                await thread.send(f'Which day? (1 for monday, 2 for tuesday, etc.)')
                day_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if day_msg is None:
                    await thread.send("No input. Request cancelled")
                    return
                day = day_msg.content.strip()
            if week is None:
                await thread.send(f'Week number? (1, 2, etc.)')
                week_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if week_msg is None:
                    await thread.send("No input. Request cancelled")
                    return
                week = week_msg.content.strip()
            if classLevel is None:
                await thread.send(f'Which level? (beg1, com, etc.)')
                cl_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if cl_msg is None:
                    await thread.send("No input. Request cancelled")
                    return
                classLevel = cl_msg.content.strip()
        except asyncio.TimeoutError:
            await thread.send("You didn't reply in time, try !drop to restart")
            return

        coach = coach.upper()
        classLevel = classLevel.upper()
        
        embed = discord.Embed(
            title="Shift drop request",
            color=discord.Color.dark_grey()
        )
        embed.description = f"""
            **Remove:** {coach}
            **Day:** {day}, Week {week}
            **Class Level:** {classLevel}
            """
        view = ConfirmView(ctx.author)

        try:
            await thread.send(embed=embed, view=view)
            await view.wait()
            if view.value:
                async with aiosqlite.connect('Coach.db') as db:
                    cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (coach,))
                    result = await cursor.fetchone()
                    if result is None:
                        await thread.send(f"Coach {coach} is not found.")
                        return
                    
                    coach_id = result[0]

                    cursor = await db.execute("""SELECT id FROM Classes
                                              WHERE day = ?
                                              AND week = ?
                                              AND level = ?;""", (day, week, classLevel,))
                    result = await cursor.fetchone()
                    if result is None:
                        await thread.send(f"Class D{day} W{week} L{classLevel} is not found.")
                        return
                    
                    class_id = result[0]

                    cursor = await db.execute("""SELECT * FROM CoachClasses
                                              WHERE class_id = ?
                                              AND coach_id = ?;""",
                                              (class_id, coach_id,))
                    result = await cursor.fetchone()
                    if result is None:
                        await thread.send(f"{coach} is not coaching this class.")
                        return                    

                    await db.execute(f"""DELETE FROM CoachClasses (class_id, coach_id)
                                     WHERE class_id = ?
                                     AND coach_id = ?;""",
                                     (class_id, coach_id,))
                    await db.commit()
                    await thread.send("All done")
            else:
                return
        except asyncio.TimeoutError:
            await thread.send("You didn't reply in time, try !drop to restart")
            return

    @commands.command()
    async def assign(self, ctx, coach = None, day = None, week = None, classLevel = None):
        """
        Assign shift

        **Usage:**
            !assign `coach` `day` `week` `class level`
        
        **Example:**
            !assign `lenin` `2` `12` `com`
        """

        if not ctx.author.id == ADMIN:
            await ctx.send("Go away")
            return

        def check(msg):
            return msg.author.id == ADMIN and msg.channel == ctx.channel
        
        thread_name = f"Drop Request - {ctx.author.display_name}"
        thread = await ctx.channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.public_thread,
            auto_archive_duration=1440
        )
        
        try:
            if coach is None:
                await thread.send(f'Coach name?')
                coach_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if coach_msg is None:
                    await thread.send("No input. Request cancelled")
                    return
                coach = coach_msg.content.strip()
            if day is None:
                await thread.send(f'Which day? (1 for monday, 2 for tuesday, etc.)')
                day_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if day_msg is None:
                    await thread.send("No input. Request cancelled")
                    return
                day = day_msg.content.strip()
            if week is None:
                await thread.send(f'Week number? (1, 2, etc.)')
                week_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if week_msg is None:
                    await thread.send("No input. Request cancelled")
                    return
                week = week_msg.content.strip()
            if classLevel is None:
                await thread.send(f'Which level? (beg1, com, etc.)')
                cl_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if cl_msg is None:
                    await thread.send("No input. Request cancelled")
                    return
                classLevel = cl_msg.content.strip()
        except asyncio.TimeoutError:
            await thread.send("You didn't reply in time, try !assign to restart")
            return

        coach = coach.upper()
        classLevel = classLevel.upper()
        
        embed = discord.Embed(
            title="Shift drop request",
            color=discord.Color.dark_grey()
        )
        embed.description = f"""
            **To:** {coach}
            **Day:** {day}, Week {week}
            **Class Level:** {classLevel}
            """
        view = ConfirmView(ctx.author)

        try:
            await thread.send(embed=embed, view=view)
            await view.wait()
            if view.value:
                async with aiosqlite.connect('Coach.db') as db:
                    cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (coach,))
                    result = await cursor.fetchone()
                    if result is None:
                        await thread.send(f"Coach {coach} is not found.")
                        return
                    
                    coach_id = result[0]

                    cursor = await db.execute("""SELECT id FROM Classes
                                              WHERE day = ?
                                              AND week = ?
                                              AND level = ?;""", (day, week, classLevel,))
                    result = await cursor.fetchone()
                    if result is None:
                        await thread.send(f"Class D{day} W{week} L{classLevel} is not found.")
                        return
                    
                    class_id = result[0]

                    await db.execute(f"""INSERT INTO CoachClasses (class_id, coach_id)
                                     VALUES (?,?);""",
                                     (class_id, coach_id,))
                    await db.commit()
            else:
                return
        except asyncio.TimeoutError:
            await thread.send("You didn't reply in time, try !assign to restart")
            return
        
    @commands.command()
    async def myshift(self, ctx, coach = None, day = None, week = None, classLevel = None):
        
        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel
        
        coach_id = None
        
        query = """SELECT Classes.week, Classes.day, Classes.level
                FROM Classes
                JOIN CoachClasses ON Classes.id = CoachClasses.class_id
                WHERE 1 = 1"""
        params = {}
        try:
            async with aiosqlite.connect('Coach.db') as db:
                if coach:
                    coach = coach.upper()
                    cursor = await db.execute("""SELECT id FROM Coaches
                                            WHERE UPPER(name) = ?;""", (coach,))
                    result = await cursor.fetchone()
                    if result is None:
                            ctx.send(f"Coach {coach} is not found.")
                            return
                    coach_id = result[0]
                if coach_id:
                    query += " AND CoachClasses.coach_id = :coach_id"
                    params["coach_id"] = coach_id
                if day:
                    query += " AND Classes.day = :day"
                    params["day"] = day
                if week:
                    query += " AND Classes.week = :week"
                    params["week"] = week
                
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                rows = sorted(rows, key=lambda x: (x["week"], x["day"]))
                data = [dict(row) for row in rows]
                if data:
                    table = tabulate(data, headers="keys", tablefmt="pretty")
                    await ctx.send(table)
                else:
                    await ctx.send("No data found.")
        except asyncio.TimeoutError:
            await ctx.send("You didn't reply in time, try !myshift to restart")


async def setup(bot):
    await bot.add_cog(BotCog(bot))