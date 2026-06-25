def content_card(c: dict) -> str:
    type_emoji = {
        "manhwa": "🇰🇷", "manga": "🇯🇵", "manhua": "🇨🇳",
        "novel": "📚", "webtoon": "🌐",
    }.get(c.get("content_type", ""), "📖")

    status_label = {
        "ongoing": "🟢 Em andamento",
        "completed": "✅ Completo",
        "hiatus": "⏸️ Hiatus",
        "upcoming": "🔜 Em breve",
    }.get(c.get("status", ""), c.get("status", ""))

    stars = "⭐" * round(c.get("average_rating", 0) / 2)
    premium = " 👑" if c.get("is_premium") else ""

    return (
        f"{type_emoji} *{c['title']}*{premium}\n"
        f"📚 {c.get('primary_genre', 'N/A')} · {status_label}\n"
        f"📖 {c.get('chapter_count', 0)} caps · {stars} {c.get('average_rating', 0):.1f}/10\n"
        f"👁️ {_fmt_num(c.get('view_count', 0))} views"
    )


def chapter_card(ch: dict) -> str:
    premium = " 👑" if ch.get("is_premium") else ""
    mins = ch.get("read_time_minutes", 0)
    return (
        f"📑 *Cap. {ch['number']}*{premium}"
        + (f" — {ch['title']}" if ch.get("title") else "")
        + f"\n⏱️ {mins} min · {_fmt_num(ch.get('word_count', 0))} palavras"
    )


def user_profile_card(u: dict, g: dict = None) -> str:
    premium = " 👑" if u.get("has_active_premium") else ""
    lines = [
        f"👤 *{u['display_name']}*{premium}",
        f"🆔 @{u['username']}" if u.get("username") else "",
        f"⚔️ Nível {u['level']} · {_fmt_num(u['total_xp'])} XP",
        f"🪙 {u.get('story_coins', 0)} StoryCoins",
        f"🔥 Streak: {u.get('current_streak', 0)} dias (recorde: {u.get('best_streak', 0)})",
    ]
    if g:
        lines.append(
            f"🏆 Conquistas: {g.get('achievements_count', 0)}/{g.get('achievements_total', 0)}"
        )
    return "\n".join(l for l in lines if l)


def xp_progress_bar(xp_in_level: int, xp_to_next: int, length: int = 10) -> str:
    pct = xp_in_level / max(xp_to_next, 1)
    filled = int(pct * length)
    return "█" * filled + "░" * (length - filled)


def _fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)
