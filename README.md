# MuffiaBot

Telegram bot moderating mafia/werewolf game. Currently supports 3 roles: `Innocent`, `Detective` and `Mafioso`.

## How to

Add this bot to group chat, preferably granting him admin rights. On `/start` command the bot issues message with game registration link. After all players have registered, you may send `/begin` command to begin the game(the game also starts after registration time has passed or max number of players was reached).

## Rules

On game beginning each player gets a role. There is usually 1 `Detective`, 1/2/3(depending on number of players) `Mafioso`, all other players are `Innocent`.

Game itself has 2 phases: night and day. During the night players with special abilities(`Detective`, `Mafioso`) are asked by the bot to perform some actions, e.g. `Detective` might kill another player or check his role, `Mafioso` vote for their victim. During the day night victims names are displayed in group chat along with their roles and all players have time to chat and determine who is `Mafioso`, the day ends with lynching vote. Only player receiving more than a half of all possible votes gets lynched with his role revealed. The game continues till all `Mafioso` are killed off or they start to dominate.