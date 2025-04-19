import os
import re
import discord
import datetime
from discord.ext import commands
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Инициализация бота
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Конфигурация
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))


class Logger:
    @staticmethod
    def create_embed(title, description, color):
        return discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

    @staticmethod
    async def send_log(embed):
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            try:
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Ошибка отправки лога: {e}")


# События бота
@bot.event
async def on_ready():
    print(f'Бот {bot.user.name} успешно запущен! (ID: {bot.user.id})')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="за сервером"))


# Участники
@bot.event
async def on_member_join(member):
    embed = Logger.create_embed(
        "🟢 Новый участник",
        f"{member.mention} присоединился к серверу\n"
        f"**Создан:** {member.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"**ID:** {member.id}",
        discord.Color.green()
    )
    await Logger.send_log(embed)


@bot.event
async def on_member_remove(member):
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    roles_text = ", ".join(roles) if roles else "Нет специальных ролей"

    # Проверка на кик
    try:
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                embed = Logger.create_embed(
                    "👢 Участник кикнут",
                    f"**Участник:** {member.mention}\n"
                    f"**ID:** {member.id}\n"
                    f"**Роли:** {roles_text}",
                    discord.Color.orange()
                )
                embed.add_field(name="Модератор", value=entry.user.mention)
                if entry.reason:
                    embed.add_field(name="Причина", value=entry.reason)
                await Logger.send_log(embed)
                return
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    embed = Logger.create_embed(
        "🔴 Участник вышел",
        f"**Участник:** {member.mention}\n"
        f"**ID:** {member.id}\n"
        f"**Роли:** {roles_text}",
        discord.Color.red()
    )
    await Logger.send_log(embed)


# Модерация
@bot.event
async def on_member_ban(guild, user):
    embed = Logger.create_embed(
        "🔨 Бан",
        f"**Участник:** {user.mention}\n"
        f"**ID:** {user.id}",
        discord.Color.dark_red()
    )

    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                embed.add_field(name="Модератор", value=entry.user.mention)
                if entry.reason:
                    embed.add_field(name="Причина", value=entry.reason)
                break
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    await Logger.send_log(embed)


@bot.event
async def on_member_unban(guild, user):
    embed = Logger.create_embed(
        "🔓 Разбан",
        f"**Участник:** {user.mention}\n"
        f"**ID:** {user.id}",
        discord.Color.green()
    )

    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
            if entry.target.id == user.id:
                embed.add_field(name="Модератор", value=entry.user.mention)
                if entry.reason:
                    embed.add_field(name="Причина", value=entry.reason)
                break
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    await Logger.send_log(embed)


@bot.event
async def on_member_update(before, after):
    # Мьют
    if before.timed_out_until != after.timed_out_until:
        if after.timed_out_until:
            embed = Logger.create_embed(
                "🔇 Мьют",
                f"**Участник:** {after.mention}\n"
                f"**До:** {after.timed_out_until.strftime('%d.%m.%Y %H:%M')}",
                discord.Color.dark_grey()
            )

            try:
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                    if entry.target.id == after.id and getattr(entry.after, "timed_out_until", None):
                        embed.add_field(name="Модератор", value=entry.user.mention)
                        if entry.reason:
                            embed.add_field(name="Причина", value=entry.reason)
                        break
            except Exception as e:
                print(f"Ошибка аудит-лога: {e}")

            await Logger.send_log(embed)
        else:
            embed = Logger.create_embed(
                "🔊 Размьют",
                f"**Участник:** {after.mention}",
                discord.Color.green()
            )

            try:
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                    if entry.target.id == after.id and not getattr(entry.after, "timed_out_until", None):
                        embed.add_field(name="Модератор", value=entry.user.mention)
                        break
            except Exception as e:
                print(f"Ошибка аудит-лога: {e}")

            await Logger.send_log(embed)

    # Изменение ролей
    if before.roles != after.roles:
        added = [role.mention for role in after.roles if role not in before.roles]
        removed = [role.mention for role in before.roles if role not in after.roles]

        if added or removed:
            embed = Logger.create_embed(
                "🎭 Изменение ролей",
                f"**Участник:** {after.mention}",
                discord.Color.blurple()
            )

            if added:
                embed.add_field(name="Добавлены", value=", ".join(added), inline=False)
            if removed:
                embed.add_field(name="Удалены", value=", ".join(removed), inline=False)

            try:
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                    if entry.target.id == after.id:
                        embed.add_field(name="Изменил", value=entry.user.mention)
                        if entry.reason:
                            embed.add_field(name="Причина", value=entry.reason)
                        break
            except Exception as e:
                print(f"Ошибка аудит-лога: {e}")

            await Logger.send_log(embed)


# Роли
@bot.event
async def on_guild_role_create(role):
    embed = Logger.create_embed(
        "➕ Создана роль",
        f"**Роль:** {role.mention}\n"
        f"**Цвет:** {str(role.color)}\n"
        f"**Права:** {len(role.permissions)}",
        discord.Color.green()
    )

    try:
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            embed.add_field(name="Создал", value=entry.user.mention)
            break
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    await Logger.send_log(embed)


@bot.event
async def on_guild_role_delete(role):
    embed = Logger.create_embed(
        "➖ Удалена роль",
        f"**Название:** {role.name}\n"
        f"**ID:** {role.id}",
        discord.Color.red()
    )

    try:
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            embed.add_field(name="Удалил", value=entry.user.mention)
            break
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    await Logger.send_log(embed)


@bot.event
async def on_guild_role_update(before, after):
    changes = []

    if before.name != after.name:
        changes.append(f"**Название:** {before.name} → {after.name}")
    if before.color != after.color:
        changes.append(f"**Цвет:** {before.color} → {after.color}")
    if before.permissions != after.permissions:
        changes.append("**Изменены права**")

    if changes:
        embed = Logger.create_embed(
            "✏️ Изменена роль",
            f"**Роль:** {after.mention}\n" + "\n".join(changes),
            discord.Color.blue()
        )

        try:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
                embed.add_field(name="Изменил", value=entry.user.mention)
                break
        except Exception as e:
            print(f"Ошибка аудит-лога: {e}")

        await Logger.send_log(embed)


# Сообщения
@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    embed = Logger.create_embed(
        "🗑️ Удалено сообщение",
        f"**Канал:** {message.channel.mention}\n"
        f"**Автор:** {message.author.mention}",
        discord.Color.red()
    )

    if message.content:
        content = message.content
        # Поиск медиа-ссылок
        media = re.findall(r'(https?://\S+\.(?:jpg|jpeg|png|gif|webp|mp3|wav|ogg))\b', content, re.IGNORECASE)
        for url in media:
            content = content.replace(url, f'[медиа]({url})')
        embed.add_field(
            name="Содержимое",
            value=content[:1000] + ("..." if len(content) > 1000 else ""),
            inline=False
        )

    if message.attachments:
        attachments = "\n".join(f'[{a.filename}]({a.url})' for a in message.attachments)
        embed.add_field(name="Вложения", value=attachments, inline=False)
        # Превью первого изображения
        for att in message.attachments:
            if any(att.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                embed.set_image(url=att.url)
                break

    try:
        async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
            if entry.target.id == message.author.id:
                embed.add_field(name="Удалил", value=entry.user.mention)
                break
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    await Logger.send_log(embed)


@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return

    embed = Logger.create_embed(
        "✏️ Изменено сообщение",
        f"**Канал:** {before.channel.mention}\n"
        f"**Автор:** {before.author.mention}\n"
        f"**[Оригинал]({before.jump_url}):** {before.content[:1000]}{'...' if len(before.content) > 1000 else ''}\n"
        f"**Изменено:** {after.content[:1000]}{'...' if len(after.content) > 1000 else ''}",
        discord.Color.blue()
    )
    await Logger.send_log(embed)


# Каналы и категории
@bot.event
async def on_guild_channel_create(channel):
    embed = Logger.create_embed(
        "✅ Создан канал",
        f"**Название:** {channel.name}\n"
        f"**Тип:** {str(channel.type).capitalize()}\n"
        f"**Категория:** {channel.category.name if channel.category else 'Нет'}",
        discord.Color.green()
    )

    try:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            embed.add_field(name="Создал", value=entry.user.mention)
            break
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    await Logger.send_log(embed)


@bot.event
async def on_guild_channel_delete(channel):
    embed = Logger.create_embed(
        "❌ Удален канал",
        f"**Название:** {channel.name}\n"
        f"**Тип:** {str(channel.type).capitalize()}\n"
        f"**Категория:** {channel.category.name if channel.category else 'Нет'}",
        discord.Color.red()
    )

    try:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            embed.add_field(name="Удалил", value=entry.user.mention)
            break
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    await Logger.send_log(embed)


@bot.event
async def on_guild_channel_update(before, after):
    changes = []

    if before.name != after.name:
        changes.append(f"**Название:** {before.name} → {after.name}")

    if isinstance(before, discord.TextChannel) and before.topic != after.topic:
        changes.append(f"**Тема:** {before.topic or 'Нет'} → {after.topic or 'Нет'}")

    if changes:
        embed = Logger.create_embed(
            "🛠️ Изменен канал",
            f"**Канал:** {after.mention}\n" + "\n".join(changes),
            discord.Color.blue()
        )
        await Logger.send_log(embed)


@bot.event
async def on_guild_category_create(category):
    embed = Logger.create_embed(
        "✅ Создана категория",
        f"**Название:** {category.name}",
        discord.Color.green()
    )

    try:
        async for entry in category.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            embed.add_field(name="Создал", value=entry.user.mention)
            break
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    await Logger.send_log(embed)


@bot.event
async def on_guild_category_delete(category):
    embed = Logger.create_embed(
        "❌ Удалена категория",
        f"**Название:** {category.name}",
        discord.Color.red()
    )

    try:
        async for entry in category.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            embed.add_field(name="Удалил", value=entry.user.mention)
            break
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    await Logger.send_log(embed)


@bot.event
async def on_guild_category_update(before, after):
    if before.name != after.name:
        embed = Logger.create_embed(
            "🛠️ Изменена категория",
            f"**Название:** {before.name} → {after.name}",
            discord.Color.blue()
        )
        await Logger.send_log(embed)


# Треды
@bot.event
async def on_thread_create(thread):
    embed = Logger.create_embed(
        "✅ Создан тред",
        f"**Название:** {thread.name}\n"
        f"**Канал:** {thread.parent.mention if thread.parent else 'Нет'}",
        discord.Color.green()
    )

    try:
        async for entry in thread.guild.audit_logs(limit=1, action=discord.AuditLogAction.thread_create):
            embed.add_field(name="Создал", value=entry.user.mention)
            break
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    await Logger.send_log(embed)


@bot.event
async def on_thread_delete(thread):
    embed = Logger.create_embed(
        "❌ Удален тред",
        f"**Название:** {thread.name}\n"
        f"**Канал:** {thread.parent.mention if thread.parent else 'Нет'}",
        discord.Color.red()
    )

    try:
        async for entry in thread.guild.audit_logs(limit=1, action=discord.AuditLogAction.thread_delete):
            embed.add_field(name="Удалил", value=entry.user.mention)
            break
    except Exception as e:
        print(f"Ошибка аудит-лога: {e}")

    await Logger.send_log(embed)


@bot.event
async def on_thread_update(before, after):
    changes = []

    if before.name != after.name:
        changes.append(f"**Название:** {before.name} → {after.name}")

    if before.archived != after.archived:
        status = "Архивирован" if after.archived else "Разархивирован"
        changes.append(f"**Статус:** {status}")

    if changes:
        embed = Logger.create_embed(
            "🛠️ Изменен тред",
            f"**Тред:** {after.mention}\n" + "\n".join(changes),
            discord.Color.blue()
        )
        await Logger.send_log(embed)


# Сервер
@bot.event
async def on_guild_update(before, after):
    changes = []

    if before.name != after.name:
        changes.append(f"**Название:** {before.name} → {after.name}")

    if before.icon != after.icon:
        changes.append("**Иконка сервера изменена**")
        if after.icon:
            changes.append(f"[Новая иконка]({after.icon.url})")

    if changes:
        embed = Logger.create_embed(
            "🛠️ Изменения сервера",
            "\n".join(changes),
            discord.Color.gold()
        )
        await Logger.send_log(embed)


# Запуск бота
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("Токен бота не найден в .env файле!")
    if not LOG_CHANNEL_ID:
        raise ValueError("ID канала для логов не найден в .env файле!")

    bot.run(TOKEN)