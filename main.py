import logging
import configparser
import datetime
import os
import shutil
import multiprocessing
import sys
import time
import curses

from RunnersManager import RunnersManager

multiprocessing.cpu_count()
from QoyodService import QoyodService

debug_step=0
if(len(sys.argv)>2):
	debug_step=int(sys.argv[2])

#Read config
config = configparser.ConfigParser()
secrets = configparser.ConfigParser()

if not config.read("settings.config"):
	print('Missing settings.config')
	exit()

if not secrets.read(".secret"):
	print('Missing .secret')
	exit()

logging.basicConfig(filename = config.get('shared','logfile'),
    format="%(asctime)s [%(levelname)s] %(message)s",level=logging.INFO,
)
logger = logging.getLogger(config.get('shared','logger'))
logger.info('New session')

if not debug_step or debug_step == 1:
	new_session = input('Starting a new session will erase data in working directory, do you want to proceed [Y/N]')
	if not debug_step and new_session.upper() != 'Y':
		logger.info('Session terminated')
		exit()
	if not debug_step and os.path.exists("working-directory"):
		shutil.rmtree('working-directory')


	start_date = input('Enter start date in YYYY-MM-DD format:\n>>')
	start_datetime=datetime.datetime.strptime(start_date, "%Y-%m-%d") 

	end_date = input('Enter end date in YYYY-MM-DD format:\n>>')
	end_datetime=datetime.datetime.strptime(end_date, "%Y-%m-%d") 
	#TODO extract validator
	if start_datetime > end_datetime:
		print('Start date cant be larger than end date!')
		logger.info('Start date larget than end date terminated')
		exit()

os.makedirs('working-directory',exist_ok=True)
os.chdir('working-directory')
if not debug_step or debug_step == 2:
	service = QoyodService(config.get("qoyod","domain"),secrets.get("qoyod","api_key"),version=config.get("qoyod","api_version"),out_file="data.json")
	print('Fetching data ...')
	found_count =service.saveInvoices(start_date,end_date,per_page=int(config.get("qoyod","per_page")))
	print('Done, saved '+str(found_count)+ ' invoices to disk')


num_of_runners = int(input('How many bot instances to use? Recommended for your device is '+str(multiprocessing.cpu_count())+ " \n>>"))
print("Running "+str(num_of_runners)+ " bots")
manager = RunnersManager(num_of_runners, in_file="data.json", out_file="data.csv")
if not debug_step or debug_step == 3:
	try:
		manager.run(secrets.get("qoyod","email"),secrets.get("qoyod","pass"))

		stdscr = curses.initscr()
		curses.noecho()
		curses.cbreak()

		while(True):
			for idx,line in enumerate(manager.get_progress_report()):
				stdscr.addstr(idx,0,line)
			stdscr.refresh()
			time.sleep(2)
			if(manager.check_all_done() == True):
				break
		manager.save_failed_runs()
	except KeyboardInterrupt:
				os._exit(0)

if not debug_step or debug_step == 4:
	print('\nPost processing data')
	manager.save_output()
	print('saved to output.csv')

print('\nfinished')