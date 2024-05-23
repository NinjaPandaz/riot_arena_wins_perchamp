from helpers import get_summoner_info, get_match_ids_by_summoner_puuid, did_player_win_match_arena, export_wins_to_google_sheets
from settings import PUUID

summoner = get_summoner_info(PUUID)
print(summoner)
#print(summoner['summonerLevel'])

summoner_match_ids = get_match_ids_by_summoner_puuid(summoner['puuid'], 25)
print(summoner_match_ids)

#win = did_player_win_match_arena(PUUID,summoner_match_ids[0])
#print(win)


match_ids = get_match_ids_by_summoner_puuid(summoner['puuid'], 25)
wins = did_player_win_match_arena(summoner['puuid'], match_ids)
print(wins)
export_wins_to_google_sheets(wins)