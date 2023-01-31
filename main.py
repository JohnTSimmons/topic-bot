import aiosqlite
import datetime
import discord
from discord.commands import Option
from discord.ext import tasks, commands
import dotenv
import os
import random

dotenv.load_dotenv()
guild_id = int(os.getenv("GUILD")) #Get the guild id for the discord server
day_id = int(os.getenv("DAY")) #Get the day of the week that we will post on.
admin_role_tag = str(os.getenv("ROLE")) #Role of the admin of the server

intents = discord.Intents.default()
intents.message_content = True #Setup our intents and tell discord we want message_content.

bot = discord.Bot(intents = intents, allowed_mentions = discord.AllowedMentions(everyone = True))

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")
    post_scheduler.datechecker.start()

@bot.slash_command(name = "hello", description = "Say hello to me!")
async def hello(ctx):
    await ctx.respond("Hey! :slight_smile:")

@bot.slash_command(name = "add_topic", description = "Submit a topic for the weekly topic!")
async def submit_topic(ctx, topic: Option(str, "Enter your message!", required = True)):
    content = topic
    author = ctx.author
    await submit_topic_into_db(content, author)
    await ctx.respond("Added topic! :white_check_mark:")

@bot.slash_command(name = "new_topic", description = "Force the bot to post a new topic, admin only.")
async def post_new_topic(ctx):
    admin_role = discord.utils.get(ctx.guild.roles, name = admin_role_tag)
    if admin_role in ctx.author.roles:
        await post_topic_of_the_week()
        await ctx.respond("Posted a new topic of the week.")
    else:
        await ctx.respond("You are not admin!")

@bot.slash_command(name = "time", description = "Debug for post scheduler.")
async def get_time(ctx):
    await ctx.channel.send("The current time is: " + str(datetime.datetime.utcnow().time()))
    await ctx.channel.send("The next task fire time is : " + str(post_scheduler.datechecker.next_iteration))
    await ctx.channel.send("The scheduler is set to fire at: " + str(post_scheduler.datechecker.time))
    await ctx.channel.send("Running? : " + str(post_scheduler.datechecker.is_running()))
    await ctx.respond(":white_check_mark: (All times UTC)")

class PostOnDay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        self.datechecker.cancel()

    async def post(self):
        await post_progress_report()
        await post_topic_of_the_week()

    @tasks.loop(time = datetime.time(20, 00)) #20 UTC corresponds to 2:00 PM CST, TODO: need to make this an env variable.
    async def datechecker(self):
        now = datetime.datetime.now()
        weekday = now.weekday()
        if weekday == day_id:
            print("Time to post!")
            await self.post()
        else:
            print("Not the correct day to post.")

    @datechecker.before_loop
    async def before_datechecker(self):
        print("Waiting...")
        await self.bot.wait_until_ready()
        print("Datechecker loop started.")

async def submit_topic_into_db(content, author):
    data = (str(content), str(author), "False")
    async with aiosqlite.connect("topic_database.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS topic_table(id INTEGER PRIMARY KEY AUTOINCREMENT, content, author, used)")
        await db.execute("INSERT INTO topic_table VALUES(null, ?, ?, ?)", data)
        await db.commit()

async def get_topic():
    async with aiosqlite.connect("topic_database.db") as db:
        cursor = await db.execute("SELECT id, content, author, used FROM topic_table WHERE used NOT LIKE 'True'")
        rows = await cursor.fetchall()
        if len(rows) > 0:
            random_topic = random.choice(rows)
            id = random_topic[0]
            cursor = await db.execute("UPDATE topic_table SET used = 'True' WHERE id = ?", str(id))
            await db.commit()
            return random_topic[1:]
        else:
            return ("There was no questions to ask!", "Error")

async def post_progress_report():
    print("Posting progress_report!")
    guild = await discord.utils.get_or_fetch(bot, 'guild', guild_id)
    channel_category = discord.utils.get(guild.categories, name = 'Progress Reports')
    channel = await guild.create_text_channel(str(datetime.date.today()), category = channel_category)
    await channel.send("@everyone it is time to post your progress for the week!")

async def post_topic_of_the_week():
    print("Posting topic of the week!")
    guild = await discord.utils.get_or_fetch(bot, 'guild', guild_id)
    channel_category = discord.utils.get(guild.categories, name = 'Topic of the Week')
    channel = await guild.create_text_channel(str(datetime.date.today()), category = channel_category)
    await channel.send("@everyone")
    topic = await get_topic()
    await channel.send(topic[1] + " asked: ")
    await channel.send(topic[0])

post_scheduler = PostOnDay(bot)

if __name__ == '__main__':
    bot.run(os.getenv('TOKEN'))
