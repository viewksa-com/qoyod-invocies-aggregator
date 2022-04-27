import json
import math
import logging
from datetime import datetime
import sys
import threading
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import re
import pytz
import base64
import time
import csv

class RunnersManager:
	def __init__(self, runners_count,in_file,out_file):
		self.logger = logging.getLogger()
		self.logger.info('Initializing runners manager, instances='+str(runners_count))
		self.base_url = 'https://www.qoyod.com/tenant/invoices/'
		self.output_file = out_file
		f= open(in_file)
		self.data = json.load(f)
		data_length = len(self.data)
		batch_size = math.ceil(data_length/runners_count)
		self.logger.info('Runners batch size= '+str(batch_size))
		valid_batches=0
		self.runners=[]
		
		for n in range(runners_count):
			batch= self.data[n*batch_size:(n+1)*batch_size]
			if(not batch):
				break
			valid_batches=valid_batches+1
			filename='temp-batch-'+str(n)+'.json'
			with open(filename, 'w') as f:
				json.dump(batch,f)
				self.runners.append({
					"id":n,
					"progress":0,
					"total": len(batch),
					"filename": filename,
					"failed_ids": [],
					"thread":None
				})
				f.close()
		self.logger.info('Prepared '+str(valid_batches)+' Runners')
	def run(self, email,password):
		self.logger.info('Started running scrappers')
		
		self.logger.info('Initializeing threads')
		for runner in self.runners:
			t = threading.Thread(target=self.__scrapper_async, args=[runner["id"],email,password])
			#t.daemon = True #die with parent
			t.start()
			runner['thread'] = t
		try:
			for runner in self.runners:
				runner['thread'].join()
		except KeyboardInterrupt:
			sys.exit()

	def __scrapper_async(self,run_id,email,qoyod_pass):
		self.logger.info('Initializing thread '+str(run_id))
		runner_data = self.runners[run_id]
		datasourcename = runner_data['filename']

		f= open(datasourcename,'r', encoding='utf-8')
		data = json.load(f)
		f.close()

		invoices_url = self.base_url
		options = Options()
		#options.add_argument('--headless')
		#options.add_argument('--disable-gpu')  # Last I checked this was necessary.

		driver = webdriver.Chrome(chrome_options=options,service=Service(ChromeDriverManager().install()))
		driver.get("https://www.qoyod.com/tenant/invoices")

		# wait for element to appear, then hover it
		wait = WebDriverWait(driver, 10)
		men_menu = wait.until(ec.visibility_of_element_located((By.XPATH, '//*[@id="user_email"]')))
		ActionChains(driver).move_to_element(men_menu).perform()

		email_field = driver.find_element_by_id('user_email')
		email_field.send_keys(email)
		
		pass_field = driver.find_element_by_id('user_password')
		pass_field.send_keys(qoyod_pass)

		login_btn = driver.find_element_by_id('login-submit')
		login_btn.click()

		# wait for element to appear, then hover it
		wait = WebDriverWait(driver, 10)
		men_menu = wait.until(ec.visibility_of_element_located((By.XPATH, '//*[@id="flash"]')))
		ActionChains(driver).move_to_element(men_menu).perform()
		self.logger.info('Thread '+str(runner_data['id'])+' is now logged in')

		csv_file = open('output-'+str(run_id)+'.csv', 'w')
		writer = csv.writer(csv_file)

		for invoice in data :
			try:
				inv_id = invoice['id']
				url=invoices_url+str(inv_id)
				driver.get(url)
				
				wait = WebDriverWait(driver, 10)
				men_menu = wait.until(ec.visibility_of_element_located((By.XPATH, '//address/span/b/a')))

				try:
					ActionChains(driver).move_to_element(men_menu).perform()
				except NoSuchElementException:
					for try_num in range(4):
						self.logger.info('trying again for possible 500 error')
						driver.get(url)
						wait = WebDriverWait(driver, 10)
						men_menu = wait.until(ec.visibility_of_element_located((By.XPATH, '//address/span/b/a')))
						if driver.find_elements(By.XPATH,'//address/span/b'):
							ActionChains(driver).move_to_element(men_menu).perform()
				addresses = driver.find_elements(By.XPATH,'//address/span/b')

				if(len(addresses)>0):
					name_field= addresses[0]
				
				# name_field = driver.find_element_by_xpath('//address/span/b/a')
				branch_field = driver.find_elements(By.XPATH,"//div[@class='form-group clearfix']//span[@class='col-xs-6 col-sm-6 pl0 pr0']")[-1]
				route_field = driver.find_element_by_xpath("//ul[@id='comments-list']//span[@class='comment-owner']")
				audit_field = driver.find_element_by_xpath("//ul[@id='comments-list']//span[@class='audit-info']")

				client_name = name_field.text
				branch_name = branch_field.text
				route_name = route_field.text


				stamp = 'N/A'
				audit_json =audit_field.get_attribute('data-data')
				if(audit_json):
					audit_data= json.loads(audit_json)
					if('approved_at' in audit_data):
						stamp=audit_data['approved_at']
					elif(invoice['qrcode_string']):
						qr=invoice['qrcode_string']
						content=base64.b64decode(qr)
						timedata=content.decode('utf-8').split('310562405700003')[1]
						utc = re.findall(r'20[0-9]{2}[0-9\-T:Z]+',timedata)[0]
						dt = datetime.strptime(utc,'%Y-%m-%dT%H:%M:%S%z')
						stamp=str(dt.astimezone(pytz.timezone('Asia/Riyadh')))
					else:
						stamp = audit_data['issue_date']
				for item in invoice['line_items']:
					vat = 'N/A'
					if(item['tax_percent'] and item['unit_price'] and item['quantity']):
						vat= float(item['tax_percent']) * float(item['unit_price']) * float(item['quantity'])/100			
					row = [invoice['reference'],item['product_name'],item['product_id'],item['quantity'],item['unit_price'],vat,client_name,route_name,invoice['issue_date'],stamp,branch_name]
					writer.writerow(row)
				csv_file.flush()
				self.runners[run_id]['progress'] = self.runners[run_id]['progress'] + 1
				time.sleep(3)
			except NoSuchElementException:
				self.logger.error('No such element error')
				self.runners[run_id]['failed_ids'].append(invoice['id'])
			except Exception as e:
				self.logger.error(e)
				self.logger.error('Error in thread '+str(run_id))
				self.runners[run_id]['failed_ids'].append(invoice['id'])
		csv_file.close()
		self.logger.info('done with thread '+str(run_id))
