import requests
from urllib.parse import urlencode
import settings
import pandas as pd
import gspread
from oauth2client.client import OAuth2Credentials
from oauth2client.client import OAuth2WebServerFlow
from time import strftime, localtime


def get_summoner_info(puuid=settings.PUUID, region=settings.DEFAULT_REGION, gameName=None,
                      tagLine=None):
    #Wrapper for SUMMONER-V4 API Portal
    #Gets information about a summoner by their puuid
    #return summoner information as a dictionary or None if theres an issue
    
    gameName = input("Please enter your summoner name, minus the tagline (#---): ")
    tagLine = input("Please enter your tagline : #")
  
    params = {
        'api_key': settings.API_KEY
    }
    api_url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
    
    try:
        response = requests.get(api_url, params=urlencode(params))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Issue getting summoner data from API: {e}")
        return None

def get_match_ids_by_summoner_puuid(puuid=settings.PUUID, matches_count=None, region=settings.DEFAULT_REGION):
    params = {
        'api_key': settings.API_KEY,
        'count': matches_count,
    }
    api_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    try:
        response = requests.get(api_url, params=urlencode(params))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f'Issues getting summoner match data from API: {e}')
        return None

def did_player_win_match_arena(puuid=settings.PUUID, match_ids=None, region=settings.DEFAULT_REGION):
    wins = []
    if match_ids is None:
        return None
    
    for match_id in match_ids:
        params = {
            'api_key': settings.API_KEY,
        }
        api_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"

        try:
            response = requests.get(api_url, params=urlencode(params))
            response.raise_for_status()
            match_data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'Issue getting match data from match id {match_id} from API: {e}')
            continue

        try:
            if 'info' in match_data and 'metadata' in match_data:
                game_mode = match_data['info']['gameMode']
                time_of_game = match_data['info']['gameStartTimestamp']
                if game_mode == 'CHERRY':  #Cherry is the code name for the arena gamemode in patch 14.9x + 
                    if puuid in match_data['metadata']['participants']:
                        player_index = match_data['metadata']['participants'].index(puuid)
                        player_info = match_data['info']['participants'][player_index]
                        champion_name = player_info['championName']
                        placement_info = player_info['placement']
                        abilities_used_info = player_info['challenges']['abilityUses']
                        dpm_info = player_info['challenges']['damagePerMinute']
                        kills_info = player_info['kills']
                        assists_info = player_info['assists']
                        deaths_info = player_info['deaths']
                        kda_info = player_info['challenges']['kda']
                        augment1 = player_info['playerAugment1']
                        augment2 = player_info['playerAugment2']
                        augment3 = player_info['playerAugment3']
                        augment4 = player_info['playerAugment4']
                        total_healed = player_info['totalHeal']
                        healing_to_others = player_info['totalHealsOnTeammates']
                        game_start = strftime('%Y-%m-%d %H:%M:%S', localtime((time_of_game/1000)))
                        cc_time = player_info['timeCCingOthers']
                        wins.append({'Win':player_info['win'], 'ChampionName': champion_name, 'MatchID': match_id, 'Placement': placement_info, 'StartTime': game_start, 
                                     'AbilitiesUsed': abilities_used_info, 'DPM': dpm_info, 'Kills': kills_info, 'Assists': assists_info, 'Deaths': deaths_info, 'KDA': kda_info,
                                     'Augment 1': augment1, 'Augment 2': augment2, 'Augment 3': augment3, 'Augment 4': augment4, 'TotalHealed': total_healed, 'HealingOthers': healing_to_others,
                                     'ccTime': cc_time})
        except KeyError as e:
            print(f"KeyError: {e} while processing match id {match_id}")
            continue

    return wins

def win_percent_of_last_20_games(puuid=settings.PUUID, region=settings.DEFAULT_REGION, region_code=settings.DEFAULT_REGION_CODE):
    summoner = get_summoner_info(puuid, region_code)
    matches = get_match_ids_by_summoner_puuid(summoner['puuid'], 20, region)

    wins = 0
    for match in matches:
        if did_player_win_match_arena(summoner['puuid'], match):
            wins += 1

    return (wins/len(matches))*100

def export_wins_to_google_sheets(wins, spreadsheet_name='League Arena Wins'):
    try:
        # Define your OAuth2.0 Client credentials
        client_id = '731446866332-kidgcno3e5sfi9uk84bgahpo5m8tjdgc.apps.googleusercontent.com'
        client_secret = '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'
        redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'

        # Create OAuth2.0 Web Server Flow
        flow = OAuth2WebServerFlow(client_id, client_secret, scope='https://spreadsheets.google.com/feeds https://www.googleapis.com/auth/drive', redirect_uri=redirect_uri)

        # Get authorization URL
        auth_uri = flow.step1_get_authorize_url()

        # Print authorization URL and prompt user to authorize
        print('Please go to the following URL and authorize access:')
        print(auth_uri)
        auth_code = input('Enter the authorization code: ')

        # Exchange authorization code for credentials
        credentials = flow.step2_exchange(auth_code)

        # Authorize the client
        client = gspread.authorize(credentials)

        # Create a new Google Sheets spreadsheet or open an existing one
        try:
            spreadsheet = client.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            spreadsheet = client.create(spreadsheet_name)

        # Select the first worksheet in the spreadsheet
        worksheet = spreadsheet.sheet1

        # Retrieve existing data from the worksheet
        expected_header = ['Win', 'Champion Name', 'Match ID', 'Placement', 'Start Time', 'Kills', 'Assists', 'Deaths', 'KDA', 'DPM', 'Total Healed', 'Healing to Others',
                           'CC Time', 'Augment 1 ID', 'Augment 2 ID', 'Augment 3 ID', 'Augment 4 ID',]
        existing_data = worksheet.get_all_records(head=1, default_blank='')

        # Extract existing MatchIds
        existing_match_ids = {entry['Match ID'] for entry in existing_data}

        print("Existing Match IDs:", existing_match_ids)

        # Append new data that isn't already in the spreadsheet based on MatchId
        for win_data in wins:
            print("Win data:", win_data)
            if 'MatchID' in win_data and win_data['MatchID'] not in existing_match_ids:
                row_data = [win_data.get('Win', ''),win_data.get('MatchID', ''), win_data.get('ChampionName', ''), win_data.get('Placement', ''), win_data.get('StartTime', ''),
                             win_data.get('Kills', ''), win_data.get('Assists', ''), win_data.get('Deaths', ''), win_data.get('KDA', ''), win_data.get('DPM', ''),
                              win_data.get('TotalHealed', ''), win_data.get('HealingOthers', ''), win_data.get('ccTime', ''), win_data.get('Augment 1', ''), win_data.get('Augment 2', ''), win_data.get('Augment 3', ''),
                               win_data.get('Augment 4', ''),]
                worksheet.append_row(row_data)
                print(f"Data appended for Match ID: {win_data['MatchID']}")
            else:
                print(f"Match ID {win_data['MatchID']} already exists in the spreadsheet.")

        print(f"Data has been successfully exported to '{spreadsheet_name}' Google Sheets.")

    except Exception as e:
        print(f"An error occurred: {e}")