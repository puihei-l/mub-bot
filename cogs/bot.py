import os
import asyncio

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from tabulate import tabulate

from ui.button import ConfirmView, TransferApprovalView

load_dotenv()

SECRETARY = int(os.getenv("SECRETARY_ID"))
ADMIN = int(os.getenv("ADMIN_ID"))
SCHEDULE_CHANNEL = int(os.getenv("SCHEDULE_ID"))

DAY_CHOICES = [
    app_commands.Choice(name="MON", value="MON"),
    app_commands.Choice(name="TUE", value="TUE"),
    app_commands.Choice(name="WED", value="WED"),
    app_commands.Choice(name="THU", value="THU"),
    app_commands.Choice(name="FRI", value="FRI"),
]

LEVEL_CHOICES = [
    app_commands.Choice(name="BEG1", value="BEG1"),
    app_commands.Choice(name="BEG2", value="BEG2"),
    app_commands.Choice(name="INT1", value="INT1"),
    app_commands.Choice(name="INT2", value="INT2"),
    app_commands.Choice(name="ADV", value="ADV"),
    app_commands.Choice(name="COM", value="COM"),
]

WEEK_CHOICES = [app_commands.Choice(name=str(i), value=i) for i in range(1, 13)]

DAY_ORDER: dict[str, int] = {"MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5}
def _is_admin(user: discord.abc.User) -> bool:
    return getattr(user, "id", None) == ADMIN


def _as_codeblock(text: str) -> str:
    return f"```{text}```"

async def _send_codeblock_chunks(interaction: discord.Interaction, text: str, *, ephemeral: bool = True):
    # Discord message limit is 2000 chars; keep some buffer for fences.
    max_chunk = 1800
    if len(text) <= max_chunk:
        await interaction.followup.send(_as_codeblock(text), ephemeral=ephemeral)
        return

    start = 0
    while start < len(text):
        chunk = text[start : start + max_chunk]
        await interaction.followup.send(_as_codeblock(chunk), ephemeral=ephemeral)
        start += max_chunk


class BotCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _db(self):
        db = getattr(self.bot, "db", None)
        if db is None:
            raise RuntimeError("Database not initialized on bot. Did setup_hook run?")
        return db

    async def _coach_autocomplete(self, interaction: discord.Interaction, current: str):
        db = self._db()
        like = f"%{current.strip().upper()}%"
        cursor = await db.execute(
            """SELECT name FROM Coaches
               WHERE UPPER(name) LIKE ?
               ORDER BY name
               LIMIT 25;""",
            (like,),
        )
        rows = await cursor.fetchall()
        return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    async def _coach_identity(self, coach_name_upper: str, guild_id: int | None):
        db = self._db()
        cursor = await db.execute(
            "SELECT id, discord_user_id, guild_id FROM Coaches WHERE UPPER(name) = ?;",
            (coach_name_upper,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        coach_id, discord_user_id, stored_guild_id = row
        # If we have guild scoping, enforce it; otherwise accept.
        if stored_guild_id is not None and guild_id is not None and int(stored_guild_id) != int(guild_id):
            return None
        return {"id": coach_id, "discord_user_id": discord_user_id, "guild_id": stored_guild_id}

    @app_commands.command(name="add_coach", description="Add a coach (admin only).")
    @app_commands.describe(name="Coach name to add")
    async def add_coach(self, interaction: discord.Interaction, name: str):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("You don't have permission to use `/add_coach`.", ephemeral=True)
            return

        coach_name = name.strip()
        if not coach_name:
            await interaction.response.send_message("Coach name can't be empty.", ephemeral=True)
            return

        db = self._db()
        cursor = await db.execute("SELECT 1 FROM Coaches WHERE UPPER(name) = ?;", (coach_name.upper(),))
        if await cursor.fetchone() is not None:
            await interaction.response.send_message(f"Coach `{coach_name}` already exists.", ephemeral=True)
            return

        await db.execute("INSERT INTO Coaches (name) VALUES (?);", (coach_name,))
        await db.commit()
        await interaction.response.send_message(f"Added coach `{coach_name}`.", ephemeral=True)

    @app_commands.command(name="remove_coach", description="Remove a coach and all their assigned shifts (admin only).")
    @app_commands.describe(coach="Coach name to remove")
    async def remove_coach(self, interaction: discord.Interaction, coach: str):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("You don't have permission to use `/remove_coach`.", ephemeral=True)
            return

        coach_name = coach.strip()
        if not coach_name:
            await interaction.response.send_message("Coach name can't be empty.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        db = self._db()
        cursor = await db.execute(
            "SELECT id, name, discord_user_id, guild_id FROM Coaches WHERE UPPER(name) = ?;",
            (coach_name.upper(),),
        )
        row = await cursor.fetchone()
        if row is None:
            await interaction.followup.send(f"Coach `{coach_name}` not found.", ephemeral=True)
            return

        coach_id, stored_name, discord_user_id, guild_id = row
        cursor = await db.execute("SELECT COUNT(*) FROM CoachClasses WHERE coach_id = ?;", (coach_id,))
        (shift_count,) = await cursor.fetchone()

        embed = discord.Embed(title="Confirm coach removal", color=discord.Color.dark_orange())
        embed.description = (
            f"**Coach:** {stored_name}\n"
            f"**Assigned shifts to remove:** {shift_count}\n"
            f"**Linked user id:** {discord_user_id or '—'}\n"
            f"**Guild id:** {guild_id or '—'}"
        )
        view = ConfirmView(interaction.user)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if not view.value:
            await interaction.followup.send("Cancelled.", ephemeral=True)
            return

        await db.execute("DELETE FROM CoachClasses WHERE coach_id = ?;", (coach_id,))
        await db.execute("DELETE FROM Coaches WHERE id = ?;", (coach_id,))
        await db.commit()

        await interaction.followup.send(f"Removed coach `{stored_name}` and {shift_count} shift assignment(s).", ephemeral=True)

    @remove_coach.autocomplete("coach")
    async def remove_coach_coach_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._coach_autocomplete(interaction, current)

    @app_commands.command(name="link_coach", description="Link a coach name to a Discord user (admin only).")
    @app_commands.describe(coach="Coach name", user="Discord user for this coach")
    async def link_coach(self, interaction: discord.Interaction, coach: str, user: discord.Member):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("You don't have permission to use `/link_coach`.", ephemeral=True)
            return

        if interaction.guild_id is None:
            await interaction.response.send_message("This must be used in a server.", ephemeral=True)
            return

        coach_u = coach.strip().upper()
        ident = await self._coach_identity(coach_u, interaction.guild_id)
        if ident is None:
            await interaction.response.send_message(f"Coach `{coach}` not found.", ephemeral=True)
            return

        db = self._db()
        await db.execute(
            "UPDATE Coaches SET discord_user_id = ?, guild_id = ? WHERE id = ?;",
            (int(user.id), int(interaction.guild_id), int(ident["id"])),
        )
        await db.commit()
        await interaction.response.send_message(f"Linked `{coach_u}` to {user.mention}.", ephemeral=True)

    @link_coach.autocomplete("coach")
    async def link_coach_coach_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._coach_autocomplete(interaction, current)

    @app_commands.command(name="bulk_remove_shifts", description="Bulk remove shifts from assignments (admin only).")
    @app_commands.describe(
        coach="Remove shifts for this coach (optional)",
        day="Day filter (optional)",
        week="Week filter (optional)",
        class_level="Level filter (optional)",
    )
    @app_commands.choices(day=DAY_CHOICES, week=WEEK_CHOICES, class_level=LEVEL_CHOICES)
    async def bulk_remove_shifts(
        self,
        interaction: discord.Interaction,
        coach: str | None = None,
        day: app_commands.Choice[str] | None = None,
        week: app_commands.Choice[int] | None = None,
        class_level: app_commands.Choice[str] | None = None,
    ):
        if not _is_admin(interaction.user):
            await interaction.response.send_message(
                "You don't have permission to use `/bulk_remove_shifts`.",
                ephemeral=True,
            )
            return

        # Safety: require at least one filter to avoid wiping everything by mistake.
        if coach is None and day is None and week is None and class_level is None:
            await interaction.response.send_message(
                "Please provide at least one filter (coach/day/week/class_level).",
                ephemeral=True,
            )
            return

        if interaction.channel is None:
            await interaction.response.send_message("This command must be used in a channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        coach_u = coach.strip().upper() if coach else None
        day_v = day.value if day else None
        week_v = week.value if week else None
        level_v = class_level.value if class_level else None

        db = self._db()

        coach_id: int | None = None
        if coach_u:
            cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (coach_u,))
            row = await cursor.fetchone()
            if row is None:
                await interaction.followup.send(f"Coach `{coach}` not found.", ephemeral=True)
                return
            coach_id = row[0]

        where = []
        params: list[object] = []
        join = ""

        if coach_id is not None:
            where.append("CoachClasses.coach_id = ?")
            params.append(coach_id)

        if day_v is not None or week_v is not None or level_v is not None:
            join = "JOIN Classes ON Classes.id = CoachClasses.class_id"
            if day_v is not None:
                where.append("Classes.day = ?")
                params.append(day_v)
            if week_v is not None:
                where.append("Classes.week = ?")
                params.append(week_v)
            if level_v is not None:
                where.append("UPPER(Classes.level) = ?")
                params.append(level_v.upper())

        where_sql = " AND ".join(where) if where else "1=1"

        # Count first for confirmation.
        cursor = await db.execute(
            f"""SELECT COUNT(*) FROM CoachClasses
                {join}
                WHERE {where_sql};""",
            params,
        )
        (count,) = await cursor.fetchone()
        if count == 0:
            await interaction.followup.send("No matching shifts found to remove.", ephemeral=True)
            return

        filt_bits = []
        if coach_u:
            filt_bits.append(f"coach={coach_u}")
        if day_v:
            filt_bits.append(f"day={day_v}")
        if week_v is not None:
            filt_bits.append(f"week={week_v}")
        if level_v:
            filt_bits.append(f"level={level_v}")

        embed = discord.Embed(title="Confirm bulk shift removal", color=discord.Color.dark_orange())
        embed.description = f"**Matching rows to remove:** {count}\n**Filters:** {', '.join(filt_bits)}"
        view = ConfirmView(interaction.user)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if not view.value:
            await interaction.followup.send("Cancelled.", ephemeral=True)
            return

        # Delete using a subquery so we can filter by Classes fields safely.
        if join:
            await db.execute(
                f"""DELETE FROM CoachClasses
                    WHERE rowid IN (
                      SELECT CoachClasses.rowid
                      FROM CoachClasses
                      {join}
                      WHERE {where_sql}
                    );""",
                params,
            )
        else:
            await db.execute(f"DELETE FROM CoachClasses WHERE {where_sql};", params)
        await db.commit()
        await interaction.followup.send(f"Removed {count} shift assignment(s).", ephemeral=True)

    @bulk_remove_shifts.autocomplete("coach")
    async def bulk_remove_shifts_coach_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._coach_autocomplete(interaction, current)

    @app_commands.command(name="all_shifts", description="View all assigned shifts (admin only).")
    @app_commands.describe(
        week="Week to view (optional — omit for all weeks)",
        day="Day filter (optional)",
        class_level="Level filter (optional)",
        coach="Coach filter (optional)",
    )
    @app_commands.choices(week=WEEK_CHOICES, day=DAY_CHOICES, class_level=LEVEL_CHOICES)
    async def all_shifts(
        self,
        interaction: discord.Interaction,
        week: app_commands.Choice[int] | None = None,
        day: app_commands.Choice[str] | None = None,
        class_level: app_commands.Choice[str] | None = None,
        coach: str | None = None,
    ):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("You don't have permission to use `/all_shifts`.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        week_v = week.value if week else None
        day_v = day.value if day else None
        level_v = class_level.value if class_level else None
        coach_u = coach.strip().upper() if coach else None

        db = self._db()

        params: list[object] = []
        where: list[str] = []

        if week_v is not None:
            where.append("Classes.week = ?")
            params.append(week_v)
        if day_v is not None:
            where.append("Classes.day = ?")
            params.append(day_v)
        if level_v is not None:
            where.append("UPPER(Classes.level) = ?")
            params.append(level_v.upper())

        if coach_u:
            cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (coach_u,))
            row = await cursor.fetchone()
            if row is None:
                await interaction.followup.send(f"Coach `{coach}` not found.", ephemeral=True)
                return
            coach_id = row[0]
            where.append("CoachClasses.coach_id = ?")
            params.append(coach_id)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"""SELECT Classes.week, Classes.day, Classes.level, Coaches.name AS coach
                FROM CoachClasses
                JOIN Classes ON Classes.id = CoachClasses.class_id
                JOIN Coaches ON Coaches.id = CoachClasses.coach_id
                {where_sql}
                ORDER BY Classes.week, Classes.day, Classes.level, Coaches.name;""",
            params,
        )
        rows = await cursor.fetchall()

        if not rows:
            await interaction.followup.send("No shifts found for that filter.", ephemeral=True)
            return

        rows = sorted(rows, key=lambda x: (x["week"], DAY_ORDER.get(x["day"], 99), x["day"], x["level"], x["coach"]))
        data = [dict(r) for r in rows]
        table = tabulate(data, headers="keys", tablefmt="pretty")
        await _send_codeblock_chunks(interaction, table, ephemeral=True)

    @all_shifts.autocomplete("coach")
    async def all_shifts_coach_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._coach_autocomplete(interaction, current)

    @app_commands.command(name="help", description="Show available commands, or help for one command.")
    @app_commands.describe(command="Specific command name, e.g. assign")
    async def help_slash(self, interaction: discord.Interaction, command: str | None = None):
        if command is None:
            embed = discord.Embed(title="Help - Commands", color=discord.Color.blue())
            embed.description = "Use `/help command:<name>` for more info on a command."

            cmds = sorted(self.bot.tree.get_commands(), key=lambda c: c.name)
            for cmd in cmds:
                if cmd.name == "help":
                    continue
                desc = cmd.description or "No description"
                embed.add_field(name=f"/{cmd.name}", value=desc, inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        cmd = discord.utils.get(self.bot.tree.get_commands(), name=command)
        if cmd is None:
            await interaction.response.send_message(f"Command `{command}` not found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Help for `/{cmd.name}`",
            color=discord.Color.dark_purple(),
            description=cmd.description or "No description",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="assignm", description="Bulk-assign all classes on a day+level to a coach (admin only).")
    @app_commands.describe(coach="Coach name", day="Day", class_level="Class level")
    @app_commands.choices(day=DAY_CHOICES, class_level=LEVEL_CHOICES)
    async def assignm(
        self,
        interaction: discord.Interaction,
        coach: str,
        day: app_commands.Choice[str],
        class_level: app_commands.Choice[str],
    ):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("You don't have permission to use `/assignm`.", ephemeral=True)
            return

        if interaction.channel is None:
            await interaction.response.send_message("This command must be used in a channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        coach_u = coach.strip().upper()
        day_u = day.value
        class_u = class_level.value

        db = self._db()
        cursor = await db.execute(
            """SELECT id FROM Classes
               WHERE day = ?
               AND UPPER(level) = ?;""",
            (day_u, class_u),
        )
        classes = await cursor.fetchall()
        if not classes:
            await interaction.followup.send(f"No {class_u} classes on day {day_u}.", ephemeral=True)
            return

        cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (coach_u,))
        coach_row = await cursor.fetchone()
        if coach_row is None:
            await interaction.followup.send(f"Coach {coach_u} is not found.", ephemeral=True)
            return

        coach_id = coach_row[0]
        for (class_id,) in classes:
            await db.execute(
                """INSERT INTO CoachClasses (class_id, coach_id)
                   VALUES (?, ?);""",
                (class_id, coach_id),
            )
        await db.commit()
        await interaction.followup.send("All done.", ephemeral=True)

    @assignm.autocomplete("coach")
    async def assignm_coach_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._coach_autocomplete(interaction, current)

    @app_commands.command(name="drop", description="Drop a shift (admin only).")
    @app_commands.describe(
        coach="Coach name (who currently has the shift)",
        to_coach="Coach name to transfer the shift to (required if you're not admin)",
        day="Day",
        week="Week number",
        class_level="Class level",
    )
    @app_commands.choices(day=DAY_CHOICES, week=WEEK_CHOICES, class_level=LEVEL_CHOICES)
    async def drop(
        self,
        interaction: discord.Interaction,
        coach: str,
        day: app_commands.Choice[str],
        week: app_commands.Choice[int],
        class_level: app_commands.Choice[str],
        to_coach: str | None = None,
    ):
        if interaction.channel is None:
            await interaction.response.send_message("This command must be used in a channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        coach_u = coach.upper()
        day_u = day.value
        week_v = week.value
        class_u = class_level.value

        is_transfer = bool(to_coach and to_coach.strip())
        if not is_transfer and not _is_admin(interaction.user):
            await interaction.followup.send(
                "Non-admins must provide `to_coach` to transfer the shift (you can't remove it).",
                ephemeral=True,
            )
            return

        to_coach_u = to_coach.strip().upper() if is_transfer else None

        # For transfers: keep a thread and require the receiving coach to approve.
        # For removals: do not create a thread; just confirm ephemerally.
        if is_transfer:
            if interaction.guild is None:
                await interaction.followup.send("Transfers must be used in a server.", ephemeral=True)
                return

            # Find the acceptor user id for the to-coach.
            ident_to = await self._coach_identity(to_coach_u, interaction.guild_id)
            if ident_to is None or not ident_to.get("discord_user_id"):
                await interaction.followup.send(
                    f"`{to_coach_u}` is not linked to a Discord user. Admin must run `/link_coach` first.",
                    ephemeral=True,
                )
                return

            acceptor = interaction.guild.get_member(int(ident_to["discord_user_id"]))
            if acceptor is None:
                acceptor = await interaction.guild.fetch_member(int(ident_to["discord_user_id"]))

            thread = await interaction.channel.create_thread(
                name=f"Drop transfer - {interaction.user.display_name}",
                type=discord.ChannelType.public_thread,
                auto_archive_duration=1440,
            )
            await interaction.followup.send(f"Created thread {thread.mention}.", ephemeral=True)

            embed = discord.Embed(title="Shift transfer request", color=discord.Color.dark_grey())
            embed.description = (
                f"**From:** {coach_u}\n**To:** {to_coach_u}\n**Day:** {day_u}, Week {week_v}\n**Class Level:** {class_u}"
            )
            view = TransferApprovalView(requester=interaction.user, acceptor=acceptor)
            await thread.send(content=f"{acceptor.mention} please approve this transfer.", embed=embed, view=view)
            await view.wait()
            if view.value is not True:
                await thread.send("Transfer not approved.")
                return
        else:
            embed = discord.Embed(title="Shift removal request", color=discord.Color.dark_grey())
            embed.description = f"**Remove:** {coach_u}\n**Day:** {day_u}, Week {week_v}\n**Class Level:** {class_u}"
            view = ConfirmView(interaction.user)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            await view.wait()
            if not view.value:
                return

        db = self._db()
        cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (coach_u,))
        coach_row = await cursor.fetchone()
        if coach_row is None:
            await interaction.followup.send(f"Coach {coach_u} is not found.", ephemeral=True)
            return
        coach_id = coach_row[0]

        to_coach_id: int | None = None
        if is_transfer:
            cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (to_coach_u,))
            to_row = await cursor.fetchone()
            if to_row is None:
                await interaction.followup.send(f"Coach {to_coach_u} is not found.", ephemeral=True)
                return
            to_coach_id = to_row[0]

        cursor = await db.execute(
            """SELECT id FROM Classes
               WHERE day = ?
               AND week = ?
               AND level = ?;""",
            (day_u, week_v, class_u),
        )
        class_row = await cursor.fetchone()
        if class_row is None:
            await interaction.followup.send(f"Class {day_u} W{week_v} L{class_u} is not found.", ephemeral=True)
            return
        class_id = class_row[0]

        cursor = await db.execute(
            """SELECT 1 FROM CoachClasses
               WHERE class_id = ?
               AND coach_id = ?;""",
            (class_id, coach_id),
        )
        if await cursor.fetchone() is None:
            await interaction.followup.send(f"{coach_u} is not coaching this class.", ephemeral=True)
            return

        # Remove from current coach
        await db.execute(
            """DELETE FROM CoachClasses
               WHERE class_id = ?
               AND coach_id = ?;""",
            (class_id, coach_id),
        )

        # Optionally transfer to another coach
        if is_transfer and to_coach_id is not None:
            await db.execute(
                """INSERT OR IGNORE INTO CoachClasses (class_id, coach_id)
                   VALUES (?, ?);""",
                (class_id, to_coach_id),
            )

        await db.commit()
        # If we created a transfer thread, report there too (so both parties can see).
        if is_transfer:
            # thread exists in the transfer branch above
            await thread.send("All done.")
        await interaction.followup.send("All done.", ephemeral=True)

    @drop.autocomplete("coach")
    async def drop_coach_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._coach_autocomplete(interaction, current)

    @drop.autocomplete("to_coach")
    async def drop_to_coach_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._coach_autocomplete(interaction, current)

    @app_commands.command(name="assign", description="Assign a shift (admin only).")
    @app_commands.describe(
        coach="Coach name",
        day="Day",
        week="Week number",
        class_level="Class level",
    )
    @app_commands.choices(day=DAY_CHOICES, week=WEEK_CHOICES, class_level=LEVEL_CHOICES)
    async def assign(
        self,
        interaction: discord.Interaction,
        coach: str,
        day: app_commands.Choice[str],
        week: app_commands.Choice[int],
        class_level: app_commands.Choice[str],
    ):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("You don't have permission to use `/assign`.", ephemeral=True)
            return

        if interaction.channel is None:
            await interaction.response.send_message("This command must be used in a channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        coach_u = coach.upper()
        day_u = day.value
        week_v = week.value
        class_u = class_level.value

        embed = discord.Embed(title="Shift assign request", color=discord.Color.dark_grey())
        embed.description = f"**To:** {coach_u}\n**Day:** {day_u}, Week {week_v}\n**Class Level:** {class_u}"
        view = ConfirmView(interaction.user)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if not view.value:
            return

        db = self._db()
        cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (coach_u,))
        coach_row = await cursor.fetchone()
        if coach_row is None:
            await thread.send(f"Coach {coach_u} is not found.")
            return
        coach_id = coach_row[0]

        cursor = await db.execute(
            """SELECT id FROM Classes
               WHERE day = ?
               AND week = ?
               AND level = ?;""",
            (day_u, week_v, class_u),
        )
        class_row = await cursor.fetchone()
        if class_row is None:
            await interaction.followup.send(f"Class {day_u} W{week_v} L{class_u} is not found.", ephemeral=True)
            return
        class_id = class_row[0]

        await db.execute(
            """INSERT INTO CoachClasses (class_id, coach_id)
               VALUES (?, ?);""",
            (class_id, coach_id),
        )
        await db.commit()

        schedule = self.bot.get_channel(SCHEDULE_CHANNEL) or await self.bot.fetch_channel(SCHEDULE_CHANNEL)

        receipt = discord.Embed(title="Shift assign receipt", color=discord.Color.dark_grey())
        receipt.description = f"**To:** {coach_u}\n**Day:** {day_u}, Week {week_v}\n**Class Level:** {class_u}"
        receipt.set_footer(text="Contact Secretary if anything is incorrect.")
        await schedule.send(embed=receipt)

        await interaction.followup.send("All done.", ephemeral=True)

    @assign.autocomplete("coach")
    async def assign_coach_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._coach_autocomplete(interaction, current)

    @app_commands.command(name="myshift", description="Check assigned shifts.")
    @app_commands.describe(
        coach="Coach name (optional)",
        day="Day (optional)",
        week="Week number (optional)",
        class_level="Class level (optional)",
    )
    @app_commands.choices(day=DAY_CHOICES, week=WEEK_CHOICES, class_level=LEVEL_CHOICES)
    async def myshift(
        self,
        interaction: discord.Interaction,
        coach: str | None = None,
        day: app_commands.Choice[str] | None = None,
        week: app_commands.Choice[int] | None = None,
        class_level: app_commands.Choice[str] | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        coach_id: int | None = None

        query = """SELECT Classes.week, Classes.day, Classes.level
                   FROM Classes
                   JOIN CoachClasses ON Classes.id = CoachClasses.class_id
                   WHERE 1 = 1"""
        params: dict[str, object] = {}

        db = self._db()
        if coach:
            coach_u = coach.upper()
            cursor = await db.execute(
                """SELECT id FROM Coaches
                   WHERE UPPER(name) = ?;""",
                (coach_u,),
            )
            row = await cursor.fetchone()
            if row is None:
                await interaction.followup.send(f"Coach {coach_u} is not found.", ephemeral=True)
                return
            coach_id = row[0]

        if coach_id is not None:
            query += " AND CoachClasses.coach_id = :coach_id"
            params["coach_id"] = coach_id
        if day:
            query += " AND Classes.day = :day"
            params["day"] = day.value
        if week:
            query += " AND Classes.week = :week"
            params["week"] = week.value
        if class_level:
            query += " AND Classes.level = :class_level"
            params["class_level"] = class_level.value

        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        rows = sorted(rows, key=lambda x: (x["week"], DAY_ORDER.get(x["day"], 99), x["day"]))
        data = [dict(r) for r in rows]
        if not data:
            await interaction.followup.send("No data found.", ephemeral=True)
            return

        table = tabulate(data, headers="keys", tablefmt="pretty")
        await interaction.followup.send(_as_codeblock(table), ephemeral=True)

    @myshift.autocomplete("coach")
    async def myshift_coach_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._coach_autocomplete(interaction, current)


async def setup(bot: commands.Bot):
    await bot.add_cog(BotCog(bot))