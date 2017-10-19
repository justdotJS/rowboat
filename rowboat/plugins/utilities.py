import random
import requests
import humanize
import operator
import gevent

from six import BytesIO
from PIL import Image
from peewee import fn
from gevent.pool import Pool
from datetime import datetime, timedelta
from collections import defaultdict

from disco.types.user import GameType, Status
from disco.types.message import MessageEmbed
from disco.util.snowflake import to_datetime
from disco.util.sanitize import S

from rowboat.plugins import RowboatPlugin as Plugin, CommandFail
from rowboat.util.timing import Eventual
from rowboat.util.input import parse_duration
from rowboat.util.gevent import wait_many
from rowboat.util.stats import statsd, to_tags
from rowboat.types.plugin import PluginConfig
from rowboat.models.guild import GuildVoiceSession
from rowboat.models.user import User, Infraction
from rowboat.models.message import Message, Reminder
from rowboat.util.images import get_dominant_colors_user, get_dominant_colors_guild
from rowboat.constants import (
    STATUS_EMOJI, SNOOZE_EMOJI, GREEN_TICK_EMOJI, GREEN_TICK_EMOJI_ID,
    EMOJI_RE, USER_MENTION_RE, YEAR_IN_SEC, CDN_URL
)
#from google import google
import random
from imagesoup import ImageSoup
soup = ImageSoup()


def search_google_images(query):
    return soup.search('"' + query + '"', n_images=300)

def small_search_google_images(query):
    return soup.search('"' + query + '"', n_images=10)

def get_status_emoji(presence):
    if presence.game and presence.game.type == GameType.STREAMING:
        return STATUS_EMOJI[GameType.STREAMING], 'Streaming'
    elif presence.status == Status.ONLINE:
        return STATUS_EMOJI[Status.ONLINE], 'Online'
    elif presence.status == Status.IDLE:
        return STATUS_EMOJI[Status.IDLE], 'Idle',
    elif presence.status == Status.DND:
        return STATUS_EMOJI[Status.DND], 'DND'
    elif presence.status in (Status.OFFLINE, Status.INVISIBLE):
        return STATUS_EMOJI[Status.OFFLINE], 'Offline'


def get_emoji_url(emoji):
    return CDN_URL.format('-'.join(
        char.encode("unicode_escape").decode("utf-8")[2:].lstrip("0")
        for char in emoji))


class UtilitiesConfig(PluginConfig):
    pass


@Plugin.with_config(UtilitiesConfig)
class UtilitiesPlugin(Plugin):
    def load(self, ctx):
        super(UtilitiesPlugin, self).load(ctx)
        self.reminder_task = Eventual(self.trigger_reminders)
        self.spawn_later(10, self.queue_reminders)

    def queue_reminders(self):
        try:
            next_reminder = Reminder.select().order_by(
                Reminder.remind_at.asc()
            ).limit(1).get()
        except Reminder.DoesNotExist:
            return

        self.reminder_task.set_next_schedule(next_reminder.remind_at)

    @Plugin.command('coin', group='random', global_=True)
    def coin(self, event):
        """
        Flip a coin
        """
        event.msg.reply(random.choice(['heads', 'tails']))

    @Plugin.command('number', '[end:int] [start:int]', group='random', global_=True)
    def random_number(self, event, end=10, start=0):
        """
        Returns a random number
        """

        # Because someone will be an idiot
        if end > 9223372036854775807:
            return event.msg.reply(':warning: ending number too big!')

        if end <= start:
            return event.msg.reply(':warning: ending number must be larger than starting number!')

        event.msg.reply(str(random.randint(start, end)))
        
    @Plugin.command('cat', global_=True)		
    def cat(self, event):		
         # Sometimes random.cat gives us gifs (smh)		
         for _ in range(3):		
             try:		
                 r = requests.get('http://random.cat/meow')		
                 r.raise_for_status()		
             except:		
                 continue		
 		
             url = r.json()['file']		
             if not url.endswith('.gif'):		
                 break		
         else:		
             return event.msg.reply('404 cat not found :(')		
 		
         r = requests.get(url)		
         r.raise_for_status()		
         event.msg.reply('', attachments=[('cat.jpg', r.content)])		
         
    @Plugin.command('dog', global_=True)
    def dog(self, event):
        # Sometimes random.dog gives us gifs (smh)
        for _ in range(3):
            try:
                r = requests.get('http://random.dog/woof.json')
                r.raise_for_status()
            except:
                continue

            url = r.json()['url']
            if not url.endswith('.gif'):
                break
        else:
            return event.msg.reply('404 dog not found :(')

        r = requests.get(url)
        r.raise_for_status()
        event.msg.reply('', attachments=[('dog.jpg', r.content)])

    @Plugin.command('image', '<quer:str>', global_=True)
    def image(self, event, quer):
        query = quer
        result = search_google_images(query)
        #if len(result < 1):
        #    return event.msg.reply("An unknown error occurred")
        choice = random.choice(result)
        r = requests.get(choice.URL)
        r.raise_for_status()
        #immg = 
        event.msg.reply('', attachments=[('img.jpg', r.content)])
        
    @Plugin.command('simage', '<quer:str>', global_=True)
    def simage(self, event, quer):
        query = quer
        result = small_search_google_images(query)
        #if len(result < 1):
        #    return event.msg.reply("An unknown error occurred")
        choice = random.choice(result)
        r = requests.get(choice.URL)
        r.raise_for_status()
        #immg = 
        event.msg.reply('', attachments=[('simg.jpg', r.content)])
        
    #@Plugin.command('apple', global_=True)
    #def apple(self, event):
       # query = "apple products"
      #  result = search_google_images(query)
      # if len(result < 1):
      #      return event.msg.reply("An unknown error occurred")
       # r = requests.get(result.link)
      ##  r.raise_for_status()
      #  event.msg.reply('', attachments=[('apple.jpg', r.content)])
                
    @Plugin.command('appl', global_=True)
    def appl(self, event):
        # Sometimes random.cat gives us gifs (smh)
        # random.dog/woof.json
        
        for _ in range(3):
            try:
                r = requests.get('http://random.dog/woof.json')
                r.raise_for_status()
            except:
                continue

            file = r.json()['file']
            if not file.endswith('.gif'):
                break
        else:
            return event.msg.reply('404 appl not found :(')

        r = requests.get(file)
        r.raise_for_status()
        event.msg.reply('', attachments=[('appl.jpg', r.content)])

    @Plugin.command('emoji', '<emoji:str>', global_=True)
    def emoji(self, event, emoji):
        if not EMOJI_RE.match(emoji):
            return event.msg.reply(u'Unknown emoji: `{}`'.format(emoji))

        fields = []

        name, eid = EMOJI_RE.findall(emoji)[0]
        fields.append('**ID:** {}'.format(eid))
        fields.append('**Name:** {}'.format(S(name)))

        guild = self.state.guilds.find_one(lambda v: eid in v.emojis)
        if guild:
            fields.append('**Guild:** {} ({})'.format(S(guild.name), guild.id))

        url = 'https://discordapp.com/api/emojis/{}.png'.format(eid)
        r = requests.get(url)
        r.raise_for_status()
        return event.msg.reply('\n'.join(fields), attachments=[('emoji.png', r.content)])

    @Plugin.command('jumbo', '<emojis:str...>', global_=True)
    def jumbo(self, event, emojis):
        urls = []

        for emoji in emojis.split(' ')[:5]:
            if EMOJI_RE.match(emoji):
                _, eid = EMOJI_RE.findall(emoji)[0]
                urls.append('https://discordapp.com/api/emojis/{}.png'.format(eid))
            else:
                urls.append(get_emoji_url(emoji))

        width, height, images = 0, 0, []

        for r in Pool(6).imap(requests.get, urls):
            try:
                r.raise_for_status()
            except requests.HTTPError:
                return

            img = Image.open(BytesIO(r.content))
            height = img.height if img.height > height else height
            width += img.width + 10
            images.append(img)

        image = Image.new('RGBA', (width, height))
        width_offset = 0
        for img in images:
            image.paste(img, (width_offset, 0))
            width_offset += img.width + 10

        combined = BytesIO()
        image.save(combined, 'png', quality=55)
        combined.seek(0)
        return event.msg.reply('', attachments=[('emoji.png', combined)])

    @Plugin.command('seen', '<user:user>', global_=True)
    def seen(self, event, user):
        try:
            msg = Message.select(Message.timestamp).where(
                Message.author_id == user.id
            ).order_by(Message.timestamp.desc()).limit(1).get()
        except Message.DoesNotExist:
            return event.msg.reply(u"I've never seen {}".format(user))

        event.msg.reply(u'I last saw {} {} ago (at 1
