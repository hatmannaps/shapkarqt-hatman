

import discord
from discord.ext import commands
from collections import Counter
from memory import _read_json

CURSE_WORDS = ["issp", "izostaveni sgradi s petyo", "pedal", "muj", "mujut", "sop"]

def analyze_user_words(user_words):
    """
    Returns stats for a single user as a dictionary:
    {
        'total_words': int,
        'curse_count': int,
        'most_common': str
    }
    """
    total = len(user_words)
    curse_count = sum(1 for w in user_words if w in CURSE_WORDS)
    most_common_word = Counter(user_words).most_common(1)
    most_common_word = most_common_word[0][0] if most_common_word else None
    return {
        "total_words": total,
        "curse_count": curse_count,
        "most_common": most_common_word
    }


async def get_server_stats(memory):
    """
    memory = {user_id: [words]}
    Returns a sorted leaderboard by curse words
    """
    leaderboard = []
    for uid, words in memory.items():
        stats = analyze_user_words(words)
        leaderboard.append((uid, stats))
    #  descending
    leaderboard.sort(key=lambda x: x[1]["curse_count"], reverse=True)
    return leaderboard


def setup(bot):
    """register serverstats"""

    @bot.command()
    async def serverstats(ctx):
        """embed."""
        memory = await _read_json()
        leaderboard = await get_server_stats(memory)

        embed = discord.Embed(title="📊 Server Stats", color=0x00ff00)
        for uid, stats in leaderboard[:10]:  # top 10 users
            member = ctx.guild.get_member(int(uid))
            if not member:
                continue
            embed.add_field(
                name=member.display_name,
                value=(
                    f"Most common word: `{stats['most_common']}`\n"
                    f"Retarded words: `{stats['curse_count']}`\n"
                    f"Total words: `{stats['total_words']}`"
                ),
                inline=False
            )

        await ctx.send(embed=embed)
