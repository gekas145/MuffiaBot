# MuffiaBot

Telegram bot moderating mafia/werewolf game. Currently supports 4 roles: `Innocent`, `Detective`, `Doctor` and `Mafioso`.

## How to

As this bot is currently not hosted anywhere, you need to host it yourself. In order to do so, you need to obtain [telegram api token](https://core.telegram.org/bots/features#botfather) and store this token as system variable under name `TELEGRAM_API_TOKEN`. Afterwards just run `main.py`.

Add this bot to group chat, preferably granting him admin rights. On `/start` command the bot issues message with game registration link. After all players have registered, you may send `/begin` command to begin the game(the game also starts after registration time has passed or max number of players was reached).

## Rules

On game beginning each player gets a role. Roles can be divided into 2 groups: innocents(`Innocent`, `Detective`, `Doctor`) and villains(`Mafioso`). Innocents aim to free their city from villains and villains want to eliminate innocents, so that they start to dominate.

Game itself has 2 phases: night and day. 

### Night

During the night players with special abilities(`Detective`, `Doctor`, `Mafioso`) are asked by the bot to perform some actions, e.g. `Mafioso` vote for their victim. 

### Day

During the day night victims names are displayed in group chat along with their roles and all alive players have time to debate and determine who is `Mafioso`, the day ends with lynching vote. Only player receiving more than a half of all possible votes gets lynched with his role revealed. 

### Game end

The game continues till all villains are killed off or they start to dominate.

### Roles

#### Innocent

Average city inhabitant. `Innocent` stays idle at night, but can participate in day lynching vote. On game start around 70% of players are `Innocent`.

#### Detective

Leader of city innocents, most powerful role after `Mafioso`. During the night can either kill another player or check his role. Usually there is 1 `Detective`.

#### Doctor

Another innocent with special ability. `Doctor` can heal one player during the night, also himself, so that this player becomes invincible for attemps to kill him. Usually there is 1 `Doctor`.

#### Mafioso

Main antagonists of the game. `Mafioso` players are aware of other mafia members and are supposed to act as a team. During the night `Mafioso` vote for their victim. Depending on overall number of players, there are usually 1 to 3 `Mafioso`. 
