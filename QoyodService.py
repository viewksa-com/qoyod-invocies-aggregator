import logging
import requests
import os
import json 

class QoyodService:
	def __init__(self, hostname,api_token,out_file= "",version='2.0'):
		self.token = api_token
		self.base_url=hostname
		self.api_version=version
		self.output_file =out_file
		self.default_headers = {
		'API-KEY': api_token
		}
		self.logger =logging.getLogger()
		self.logger.info('Starting Qoyod service')
		self.per_page=100

	def saveInvoices(self,start_date,end_date,per_page=0):
		self.logger.info('Fetching invoices from '+start_date+' to '+end_date)
		if per_page == 0:
			per_page=self.per_page
		page =1
		params = {
			"q[issue_date_gteq]":start_date,
			"q[issue_date_lt]": end_date,
			"q[s]": "issue_date asc",
			"per_page": per_page,
			"page": page
		}
		data = []
		response = requests.request("GET",self.__getServiceUrl('invoices'),headers=self.default_headers,params=params)
		
		while response.status_code == 200:
			page_data =response.json()['invoices'];
			data.extend(page_data)
			page_length = len(page_data)
			self.logger.info("Page "+str(page)+ " Fetched "+str(page_length)+ " invoices")
			if page_length < self.per_page:
				break
			page = page +1
			params["page"]=page
			response = requests.request("GET",self.__getServiceUrl('invoices'),headers=self.default_headers,params=params)
	
		if len(data) == 0:
			self.logger.error('Found no data fetching for specified date range')
		
		if self.output_file:
			with open(self.output_file,'w') as f:
				json.dump(data,f)
				f.close();
				return len(data)

		return 0
		
		
	def __getServiceUrl(self,service_name):
		return self.base_url+"/api/"+self.api_version+"/"+service_name;
