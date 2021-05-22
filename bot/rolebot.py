import discord as d
from discord.ext import commands as com

import json
import pickle
import os

class dotdict(dict):
   __getattr__ = dict.get
   __setattr__ = dict.__setitem__
   __delattr__ = dict.__delitem__

with open('../config.json', 'r') as f:
   config = json.loads(f.read(), object_pairs_hook=dotdict)

bot = com.Bot(command_prefix=('!'))

DATNAME = "react_roles.data"
react_roles = None

def persist_roles():
   with open(DATNAME, 'wb') as f:
      pickle.dump(react_roles,f)

if os.path.exists(DATNAME):
   with open(DATNAME, 'rb') as f:
      react_roles = pickle.load(f)

@bot.event
async def on_ready():
   global guild, react_roles, role_channel, role_message
   guild = d.utils.get(bot.guilds, name=config.server_name)
   print(f"Bot connected to {guild}")
   channels = await guild.fetch_channels()
   if react_roles is None:
      react_roles = {}
   role_channel = d.utils.get(channels, name=config.role_channel)
   role_message = None
   async for message in role_channel.history(limit = 1, oldest_first=True):
      role_message = message
   
@bot.event
async def on_raw_reaction_add(payload):
   if payload.event_type != 'REACTION_ADD':
      return
   payload_guild = await bot.fetch_guild(payload.guild_id)
   if payload_guild != guild:
      return
   react_mem = payload.member
   if react_mem == guild.me:
      return
   channel = await bot.fetch_channel(payload.channel_id)
   if channel is None:
      return
   message = await channel.fetch_message(payload.message_id)
   if message is None or role_message is None or message.id != role_message.id:
      return

   emoji = payload.emoji
   if emoji is None or emoji not in react_roles:
      return
   roles = await guild.fetch_roles()
   react_role = d.utils.get(roles, id=react_roles[emoji])
   await react_mem.add_roles(react_role)
   
@bot.event
async def on_raw_reaction_remove(payload):
   if payload.event_type != 'REACTION_REMOVE':
      return
   payload_guild = await bot.fetch_guild(payload.guild_id)
   if payload_guild != guild:
      return
   react_mem = await guild.fetch_member(payload.user_id)
   if react_mem == guild.me:
      return
   channel = await bot.fetch_channel(payload.channel_id)
   if channel is None:
      return
   message = await channel.fetch_message(payload.message_id)
   if message is None or role_message is None or message.id != role_message.id:
      return

   emoji = payload.emoji
   if emoji is None or emoji not in react_roles:
      return
   roles = await guild.fetch_roles()
   react_role = d.utils.get(roles, id=react_roles[emoji])
   await react_mem.remove_roles(react_role)

@bot.command()
async def addrole(ctx, role_name, emoji):
   if ctx.guild != guild:
      return
   mem = ctx.author
   admin_role = d.utils.get(mem.roles, name=config.admin_role)
   if admin_role is None:
      return

   try:
      await ctx.message.add_reaction(emoji)
   except (d.errors.HTTPException, d.errors.NotFound, d.errors.InvalidArgument):
      await ctx.channel.send(f'"{emoji}" is not an emoji that can be added as a reaction on this server.')
      return
   message = await ctx.channel.fetch_message(ctx.message.id)
   await ctx.message.remove_reaction(emoji, guild.me)
   if len(message.reactions) != 1:
      await ctx.channel.send('Do not add any reactions to the command message!')
      return
   emoji = message.reactions[0].emoji
   if isinstance(emoji, str):
      emoji = d.PartialEmoji(animated=False, name=emoji)
   elif isinstance(emoji, d.Emoji):
      emoji = d.PartialEmoji(animated=emoji.animated,id=emoji.id,name=emoji.name)
   if emoji in react_roles:
      await ctx.channel.send(f'There is already a reaction role for the emoji "{emoji}"!')
      return
   
   roles = await guild.fetch_roles()
   react_role = d.utils.get(roles, name=role_name)
   if react_role is not None:
      await ctx.channel.send(f'Cannot create a role listener for an existing role!')
      return
   react_role = await guild.create_role(name=role_name, mentionable=True, reason="Add reaction role with !addrole.")
   react_roles[emoji] = react_role.id
   persist_roles()
   if role_message is None:
      await refresh(ctx)
   if role_message is not None:
      await role_message.add_reaction(emoji)
      await ctx.channel.send('Successfully created reaction role!')
   else:
      await ctx.channel.send(f'Create a role message in {role_channel}, and then run `!refresh`.') 

@bot.command()
async def removerole(ctx, emoji):
   if ctx.guild != guild:
      return
   mem = ctx.author
   admin_role = d.utils.get(mem.roles, name=config.admin_role)
   if admin_role is None:
      return

   try:
      await ctx.message.add_reaction(emoji)
   except (d.errors.HTTPException, d.errors.NotFound, d.errors.InvalidArgument):
      await ctx.channel.send(f'"{emoji}" is not an emoji that can be added as a reaction on this server.')
      return
   message = await ctx.channel.fetch_message(ctx.message.id)
   await ctx.message.remove_reaction(emoji, guild.me)
   if len(message.reactions) != 1:
      await ctx.channel.send('Do not add any reactions to the command message!')
      return
   emoji = message.reactions[0].emoji
   if isinstance(emoji, str):
      emoji = d.PartialEmoji(name = emoji)
   elif isinstance(emoji, d.Emoji):
      emoji = d.PartialEmoji(animated=emoji.animated,id=emoji.id,name=emoji.name)

   if emoji not in react_roles:
      await ctx.channel.send('There is no reaction role listener for the emoji "{emoji}"')
      return

   roles = await guild.fetch_roles()
   react_role = d.utils.get(roles, id=react_roles[emoji])
   await role_message.clear_reaction(emoji)
   await react_role.delete()
   del react_roles[emoji]
   persist_roles()
   await ctx.channel.send('Successfuly removed reaction role!')

@bot.command()
async def refresh(ctx):
   if ctx.guild != guild:
      return
   mem = ctx.author
   admin_role = d.utils.get(mem.roles, name=config.admin_role)
   if admin_role is None:
      return

   role_message = None
   async for message in role_channel.history(limit = 1, oldest_first=True):
      role_message = message
   if role_message is not None:
      for emoji in react_roles:
         await role_message.add_reaction(emoji)

bot.run(config.token)

