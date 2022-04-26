import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import re
from datetime import datetime
import pytz
import base64

run_id = -1
import sys
if(len(sys.argv)>2):
	run_id=int(sys.argv[2])

import time
import csv
csv_file = open('output-'+str(run_id)+'.csv', 'w')


f = open('pass')
qoyod_pass = f.read()
f.close()
datasourcename = 'invoices-api.json';
if(run_id > 0):
	datasourcename='invoices-api-P'+str(run_id)+'.json'
f= open(datasourcename,'r', encoding='utf-8')
data = json.load(f)

invoices_url = 'https://www.qoyod.com/tenant/invoices/'
count = 0

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')  # Last I checked this was necessary.

driver = webdriver.Chrome(chrome_options=options,service=Service(ChromeDriverManager().install()))
driver.get("https://www.qoyod.com/tenant/invoices")

# wait for element to appear, then hover it
wait = WebDriverWait(driver, 10)
men_menu = wait.until(ec.visibility_of_element_located((By.XPATH, '//*[@id="user_email"]')))
ActionChains(driver).move_to_element(men_menu).perform()

email_field = driver.find_element_by_id('user_email')
email_field.send_keys('md.hawamdeh@gmail.com');


pass_field = driver.find_element_by_id('user_password')
pass_field.send_keys(qoyod_pass);

login_btn = driver.find_element_by_id('login-submit')
login_btn.click()

# wait for element to appear, then hover it
wait = WebDriverWait(driver, 10)
men_menu = wait.until(ec.visibility_of_element_located((By.XPATH, '//*[@id="flash"]')))
ActionChains(driver).move_to_element(men_menu).perform()

writer = csv.writer(csv_file)


#missed runs
# retry_file = open('missed ids','r')
# lines = retry_file.read().splitlines()
retry_file = open('missed ids','w')
retry_run = False
#####
for invoice in data :
	try:
		if(retry_run and (str(invoice['id']) in lines) == False):
			continue
		inv_id = invoice['id']
		url=invoices_url+str(inv_id)
		driver.get(url)
		wait = WebDriverWait(driver, 10)
		men_menu = wait.until(ec.visibility_of_element_located((By.XPATH, '//address/span/b/a')))
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
		count = count + 1
		time.sleep(3)
	except Exception as e:
		retry_file.write(str(invoice['id']))
		retry_file.flush()
csv_file.close()
retry_file.close()


print (count)

