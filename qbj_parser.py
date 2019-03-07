import json
import sys

# Gets a team by their ref string (id) from a list of teams
def get_team_index(ref, team_list):
	for i in range(len(team_list)):
		if team_list[i]['id'] == ref:
			return i
	
	return -1
	
# Gets a player by their ref string (id) from a team
def get_player_index(ref, team):
	for i in range(len(team['players'])):
		if team['players'][i]['id'] == ref:
			return i
			
	return None
	
def get_round(tournament, match_ref):
	round_list = tournament['phases'][0]['rounds']
	for i in range(len(round_list)):
		for match in round_list[i]['matches']:
			if match['$ref'] == match_ref:
				return (i + 1)
	
	return -1

# Checks if school names and team names are unique across the entire tournament
def is_team_unique(new_team, team_list):		
	for old_team in team_list:
		if new_team['name'] == old_team['name']:
			print('Team ' + new_team['name'] + ' is not unique')
			return False
		else:
			if not are_players_unique(new_team):
				return False
				
	return True
	
# Checks if player names are unique within each team
def are_players_unique(team):
	player_names = []
	for player in team['players']:
		new_name = player['name']
		for old_name in player_names:
			if new_name == old_name:
				print('Player ' + new_name + ' on team ' + team['name'] + ' is not unique')
				return False
			else:
				player_names.append(new_name)
	
	return True	
	
# Adds team to team list, does some verification
def add_team(new_reg, team_list):
	for team in new_reg['teams']:
		if is_team_unique(team, team_list):
			team_list.append(team)
		else:
			sys.exit(1)

def add_score_info(match_team, match, players_per_team):
	match_team['total_buzzes'] = 0
	match_team['total_correct'] = 0
	match_team['buzz_points'] = 0
	combined_tuh = 0
	for player in match_team['match_players']:
		combined_tuh += player['tossups_heard']
		player['score'] = 0
		player_correct = 0
		player_buzzes = 0
		player['answer_counts'] = sorted(player['answer_counts'], key=lambda k: k['answer_type']['value'], reverse=True)
		for value in player['answer_counts']:
			point_val = value['answer_type']['value']
			point_num = value['number']
			if point_num < 0:
				print('Player ' + player['player']['$ref'] + ' has a negative amount of ' + str(point_val) + 's in match ' + match['id'])
				sys.exit(1)
				
			player['score'] += (point_val * point_num)
			if point_val < 0: # negs
				player_buzzes += value['number']
			else:
				player_buzzes += value['number']
				player_correct += value['number']
		
		# value loop is done
		if player_buzzes > player['tossups_heard']:
			print('Player ' + player['player']['$ref'] + ' in match ' + match['id'] + 'has too many buzzes')
			sys.exit(1)
		else:
			match_team['total_buzzes'] += player_buzzes
			match_team['total_correct'] += player_correct
			match_team['buzz_points'] += player['score']
	
	# player loop done
	if match_team['total_buzzes'] > match['tossups_read']:
		print('Team ' + match_team['team'['$ref']] + ' has too many buzzes')
		sys.exit(1)
	
	if combined_tuh > (match['tossups_read'] + match['overtime_tossups_read']) * players_per_team:
		print('TUH in match ' + match['id'] + ' is bad')
		sys.exit(1)
	
	# TODO: move to after overtime adjustment
	match_team['bonus_points'] = match_team['points'] - match_team['buzz_points'] - match_team['bonus_bounceback_points']
	if match_team['total_correct'] != 0:
		ppb = float(match_team['bonus_points']) / match_team['total_correct']
		if ppb < 0 or ppb > 30:
			print('PPB for team ' + match_team['team']['$ref'] + ' in match ' + match['id'] + ' is ' + str(ppb))
			print(match_team['bonus_points'], match_team['total_correct'])
			sys.exit(1)
	
# Checks if match has proper data, calculates other info
def verify_match(match, tpm, bouncebacks, players_per_team):
	left_team = match['match_teams'][0]
	right_team = match['match_teams'][1]
	if left_team['team']['$ref'] == right_team['team']['$ref']:
		print('Teams in match ' + match['id'] + ' are the same')
		return False
	
	add_score_info(left_team, match, players_per_team)
	add_score_info(right_team, match, players_per_team)
	
	if (left_team['total_correct'] + right_team['total_correct']) > match['tossups_read']:
		print('Questions answered greater than tossups read in match ' + match['id'])
		sys.exit(1)
	
	# Adjust for overtime
	if match['tossups_read'] > tpm:
		match['overtime_tossups_read'] = match['tossups_read'] - tpm
		if left_team['points'] > right_team['points']:
			left_team['bonuses_heard'] = left_team['total_correct'] - match['overtime_tossups_read']
			right_team['bonuses_heard'] = right_team['total_correct']
		else:
			right_team['bonuses_heard'] = right_team['total_correct'] - match['overtime_tossups_read']
			left_team['bonuses_heard'] = left_team['total_correct']
	else:
		match['overtime_tossups_read'] = 0
		left_team['bonuses_heard'] = left_team['total_correct']
		right_team['bonuses_heard'] = right_team['total_correct']
	
	return True
			
# Adds match to match list after verification
def add_match(new_match, match_list, tpm, bouncebacks, players_per_team):
	if verify_match(new_match, tpm, bouncebacks, players_per_team):
		match_list.append(new_match)
	else:
		sys.exit(1)
	
# Gives each team a "pool" field containing the name of the pool that team is in
def assign_pools(settings, team_list):
	if len(settings['pools']) == 0:
		for team in team_list:
			team['pool'] = -1
	else:
		for team in team_list:
			for pool_idx in range(len(settings['pools'])):
				team_found = False
				for pool_team in settings['pools'][pool_idx]['teams']:
					if team['name'] == pool_team:
						team['pool'] = pool_idx
						team_found = True
						break
				if team_found:
					break
			if 'pool' not in team:
				print('Pools used, but team ' + team['name'] + ' is not assigned to a pool. Have you tried escaping quote characters?')
				sys.exit(1)

# Prints/writes to file based on boolean value: 1 if true, 0 if false
def parse_boolean(val):
	if val:
		print(1, file=sqbs_file)
	else:
		print(0, file=sqbs_file)
		
def write_player(index, player_team, teams, sqbs_file):
	try:
		team = teams[get_team_index(player_team['team']['$ref'], teams)]
		player = player_team['match_players'][index]
		print(get_player_index(player['player']['$ref'], team), file=sqbs_file) # player index
		gp = float(player['tossups_heard']) / match['tossups_read']
		if gp == 1.0:
			print(1, file=sqbs_file)
		else:
			gp_str = '%.6f' % gp
			print(gp_str.rstrip('0'), file=sqbs_file)
		for i in range(4):
			try:
				print(player['answer_counts'][i]['number'], file=sqbs_file)
			except IndexError:
				print(0, file=sqbs_file) # option not used
		print(player['score'], file=sqbs_file) # total points scored
	except IndexError:
		print(-1, file=sqbs_file) # player unused
		print(0, file=sqbs_file) # GP
		print(0, file=sqbs_file) # first point value
		print(0, file=sqbs_file) # second point value
		print(0, file=sqbs_file) # third point value
		print(0, file=sqbs_file) # fourth point value
		print(0, file=sqbs_file) # total points scored
		
	
# need info on phases, pools, settings, forfeits
# print('Assumes overtime is tossups without bonuses')
if len(sys.argv) != 3:
	print('Usage: qbj_parser.py <qbj_file> <settings_file>')
	sys.exit(1)
	
with open(sys.argv[1]) as qbj_file:
	qbj_data = json.load(qbj_file)
with open(sys.argv[2]) as settings_file:
	settings = json.load(settings_file)

# see https://www.qbwiki.com/wiki/SQBS_data_file
# and http://schema.quizbowl.technology/
qbj_objects = qbj_data['objects']

teams = []
matches = []

for item in qbj_objects:
	type = item['type']
	if type == 'Tournament':
		tournament = item
		tournament['scoring_rules']['answer_types'] = sorted(tournament['scoring_rules']['answer_types'], key=lambda k: k['value'], reverse=True)
	elif type == 'Registration':
		add_team(item, teams)
	elif type == 'Match':
		add_match(item, matches, item['tossups_read'], tournament['scoring_rules']['bonuses_bounce_back'], tournament['scoring_rules']['maximum_players_per_team'])
	else:
		continue

assign_pools(settings, teams)
		
sqbs_file = open(settings['tournament_name'].replace(' ', '_') + '.sqbs', 'w')
print(len(teams), file=sqbs_file)

for team in teams:
	print(1 + len(team['players']), file=sqbs_file)
	print(team['name'], file=sqbs_file)
	for player in team['players']:
		print(player['name'], file=sqbs_file)
		
print(len(matches), file=sqbs_file)

match_num = 0
for match in matches:
	print(match_num, file=sqbs_file)
	match_num += 1
	
	left_team = match['match_teams'][0]
	right_team = match['match_teams'][1]
	print(get_team_index(left_team['team']['$ref'], teams), file=sqbs_file)
	print(get_team_index(right_team['team']['$ref'], teams), file=sqbs_file)
	print(left_team['points'], file=sqbs_file)
	print(right_team['points'], file=sqbs_file)
	print(match['tossups_read'], file=sqbs_file)
	round_num = get_round(tournament, match['id'])
	print(round_num, file=sqbs_file)
	
	if tournament['scoring_rules']['bonuses_bounce_back']: # bonus stuff
		print(left_team['bonuses_heard'] + (10000 * right_team['total_correct']), file=sqbs_file)
		print(left_team['bonus_points'] + (10000 * left_team['bonus_bounceback_points']), file=sqbs_file)
		print(right_team['bonuses_heard'] + (10000 * left_team['total_correct']), file=sqbs_file)
		print(right_team['bonus_points'] + (10000 * right_team['bonus_bounceback_points']), file=sqbs_file)
	else:
		print(left_team['bonuses_heard'], file=sqbs_file)
		print(left_team['bonus_points'], file=sqbs_file)
		print(right_team['bonuses_heard'], file=sqbs_file)
		print(right_team['bonus_points'], file=sqbs_file)
	
	if match['overtime_tossups_read'] == 0:
		print(0, file=sqbs_file)
		print(0, file=sqbs_file) # left team overtime tossups gotten
		print(0, file=sqbs_file) # right team overtime tossups gotten
	else:
		print(1, file=sqbs_file)
		print(left_team['total_correct'] - left_team['bonuses_heard'], file=sqbs_file)
		print(right_team['total_correct'] - right_team['bonuses_heard'], file=sqbs_file)
		
	print(0, file=sqbs_file) # forfeit
	print(0, file=sqbs_file) # left team lightning round
	print(0, file=sqbs_file) # right team lightning round
	for i in range(8):
		write_player(i, left_team, teams, sqbs_file)
		write_player(i, right_team, teams, sqbs_file)
	
if settings['bonus_tracking'] == 0: #If "Bonus Conversion Tracking" (in tournament setup) is "None" then 0, otherwise 1
	print(0, file=sqbs_file)		#If "Bonus Conversion Tracking" (in tournament setup) is "Automatic" then 1, if "None" then 0, if "Manual Hrd, Auto Pts" then 2, if "Manual with Bouncebacks" then 3
	print(0, file=sqbs_file)
else:
	print(1, file=sqbs_file)
	print(settings['bonus_tracking'], file=sqbs_file)
if settings['track_powers_negs']: #If "Track Power and Neg Stats" is enabled (in tournament setup) then 3, otherwise 2
	print(3, file=sqbs_file)
else:
	print(2, file=sqbs_file)
print(0, file=sqbs_file) 	#If "Track Lightning Round Stats" is enabled (in tournament setup) then 1, otherwise 0
parse_boolean(settings['track_tuh']) #If "Track Toss-Ups Heard" is enabled (in tournament setup) then 1, otherwise 0
if settings['sort_players_by_pts_tuh']: #If "Sort Players by Pts/TUH" is enabled (in the Sorting tab of Settings) then 1, otherwise 0
	print(3, file=sqbs_file)
else:
	print(2, file=sqbs_file)
	
print(254, file=sqbs_file) #A bit mask for the "Warnings" tab in Settings. Start with 0; add 128 if the first is enabled, add 64 if the second is enabled, and so on, up to adding 2 if the seventh is enabled, so 254 represents all warnings enabled.

parse_boolean(settings['round_rep']) #If round report is enabled (in the Reports tab of Settings) then 1, otherwise 0
parse_boolean(settings['team_standings']) #If team standings report is enabled (in the Reports tab of Settings) then 1, otherwise 0
parse_boolean(settings['ind_standings']) #If individual standings report is enabled (in the Reports tab of Settings) then 1, otherwise 0
parse_boolean(settings['scoreboard']) #If scoreboard report is enabled (in the Reports tab of Settings) then 1, otherwise 0
parse_boolean(settings['team_detail']) #If team detail report is enabled (in the Reports tab of Settings) then 1, otherwise 0
parse_boolean(settings['ind_detail']) #If individual detail report is enabled (in the Reports tab of Settings) then 1, otherwise 0
parse_boolean(settings['stat_key']) #If the "stat key" for web reports is enabled (in the Reports tab of Settings) then 1, otherwise 0
print(0, file=sqbs_file) #If a custom stylesheet for web reports is specified (in the Reports tab of Settings) then 1, otherwise 0

if len(settings['pools']) == 0: #If "Use Divisions" is enabled (in the General tab of Settings) then 1, otherwise 0
	print(0, file=sqbs_file)
else:
	print(1, file=sqbs_file)
	
print(1, file=sqbs_file) #The 1-based index of the sort method chosen in the Sorting tab of Settings. (1 is for "Record, PPG", …, 5 is for "Record, Head-to-Head, PPTH")

print(settings['tournament_name'], file=sqbs_file) #Tournament name
print(settings['ftp_host_addr'], file=sqbs_file) #The Host Address (from the FTP tab of Settings)
print(settings['ftp_username'], file=sqbs_file) #The User Name (from the FTP tab of Settings)
print(settings['ftp_dir'], file=sqbs_file) #The Directory (from the FTP tab of Settings)
print(settings['ftp_base_filename'], file=sqbs_file) #The Base File Name (from the FTP tab of Settings)

print(1, file=sqbs_file) #If "Always use '/' in paths" in the FTP tab of settings is false, and "British-Style Reports" in the Reports tab of settings is false, then 0. If /-in-paths is true and British is false, then 1. If /-in-paths is false and British is true, then 2. If both are true, then 3. (This is oddly complex; one assumes that this line originally represented just "Always use '/' in paths", then the "British-Style Reports" option was created later and its value incorporated into this line to avoid breaking backward-compatibility.)


print('_rounds.html', file=sqbs_file) #The file suffix next to "Include Round Reports" (in the Reports tab of Settings)
print('_standings.html', file=sqbs_file) #The file suffix next to "Include Team Standings" (in the Reports tab of Settings)
print('_individuals.html', file=sqbs_file) #The file suffix next to "Include Individual Standings" (in the Reports tab of Settings)
print('_games.html', file=sqbs_file) #The file suffix next to "Include Scoreboard" (in the Reports tab of Settings)
print('_teamdetail.html', file=sqbs_file) #The file suffix next to "Include Team Detail" (in the Reports tab of Settings)
print('_playerdetail.html', file=sqbs_file) #The file suffix next to "Include Individual Detail" (in the Reports tab of Settings)
print('_statkey.html', file=sqbs_file) #The file suffix next to "Include Stat Key" (in the Reports tab of Settings)
print('', file=sqbs_file) #The file name next to "Use Style Sheet" (in the Reports tab of Settings)

print(len(settings['pools']), file=sqbs_file) #If Divisions [i.e., pools] are used, then the number of Divisions, otherwise 0
for pool in settings['pools']: #If Divisions are used, then the name of each Division in order (This leaf node in our documentation represents as many lines as there are Divisions, which may be no lines at all.)
	print(pool['name'], file=sqbs_file)
print(len(teams), file=sqbs_file) #The number of teams
for team in teams: #For each team according to its index, the (0-based) index of the Division it is assigned to, or -1 if Divisions are not used. (This leaf node in our documentation represents as many lines as there are teams.)
	print(team['pool'], file=sqbs_file)

for i in range(4): # point value slots
	try:
		print(tournament['scoring_rules']['answer_types'][i]['value'], file=sqbs_file)
	except IndexError:
		print(0, file=sqbs_file)

print(0, file=sqbs_file) #If packet names are used, then the number of packet names, otherwise 0
#If packet names are used, then each packet name in order. (This leaf node in our documentation represents as many lines as there are packet names specified, which might be no lines at all.)

print(len(teams), file=sqbs_file) #The number of teams
for team in teams: #For each team according to its index, 1 if it is an exhibition team, otherwise 0. (This leaf node in our documentation represents as many lines as there are teams.)
	print(0, file=sqbs_file)
	
sqbs_file.close()
