#This script will initate a connection to Constellix, check the status of the failover records, and compare them to the Cloudflare configuration. It will then update the record Cloudflare points to based on what failover record Constellix is using

import hashlib
import hmac
import base64
import requests
import json
import time

cloudflareip = ''
cloudflarerecordid = ''
siteip = ''


#all variables needed in case we need to make a request later
cloudflare_name = ''
cloudflare_proxied = ''
cloudflare_settings =''
cloudflare_tags = ''
cloudflare_ttl = ''
cloudflare_content = ''
cloudflare_type = ''

#Function to create hash of the time and constellix API secret
def create_hmac_sha1(time, secret_key):
    # Create a new HMAC object using the secret key and SHA1 hash algorithm
    hmac_obj = hmac.new(secret_key.encode(), time.encode(), hashlib.sha1)
    
    # Generate the HMAC and encode it in Base64
    hmac_base64 = base64.b64encode(hmac_obj.digest()).decode()
    
    return hmac_base64

#Gets the epoch time for the request and generates a hash using the epoch time and Constellix API secret
epoch = int(time.time() * 1000)
epoch = str(epoch)
timehash = create_hmac_sha1(epoch, 'constellix-secret-key')

#combines the fields into a token
token = 'constellix-api-token' + ':' + timehash + ':' + epoch 

#sets the Constellix API parameters
constellix_api_url = "https://api.dns.constellix.com/v1/domains/domainid/records/A/recordnumber"
constellix_payload={}
constellix_headers = {
  'Content-Type': 'application/json',
  'x-cns-security-token': token
}
#get the response
constellix_response = requests.request("GET", constellix_api_url, headers=constellix_headers, data=constellix_payload)

#load the JSON response
constellix_response_json = json.loads(constellix_response.text)

#set variables based on the JSON response
mainip = constellix_response_json['failover']['values'][0]['value']
mainipstatus = constellix_response_json['failover']['values'][0]['status']
secondaryip = constellix_response_json['failover']['values'][1]['value']
secondaryipstatus = constellix_response_json['failover']['values'][1]['status']

#debug output
print('main ip is ' + mainip)
print('main ip status is '+ mainipstatus)
print('secondary ip is ' + secondaryip)
print('secondary ip status is ' + secondaryipstatus)

#sets the Cloudflare API URL
cloudflare_url = 'https://api.cloudflare.com/client/v4/zones/zone-id/dns_records'

#sets the Cloudflare API Headers
cloudflare_headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer cloudflare-bearer'
}

#Calls the Cloudflare API
cloudflare_response = requests.request("GET", cloudflare_url, headers=cloudflare_headers)

#load the JSON repsponse
cloudflare_response_json = json.loads(cloudflare_response.text)

for x in cloudflare_response_json['result']:
    if(x['name'] == 'failoverexample.example.com'):
        cloudflareip = x['content']
        cloudflarerecordid=x['id']
        print('cloudflare ip is '+ cloudflareip)
        cloudflare_name = x['name']
        cloudflare_proxied = x['proxied']
        cloudflare_settings = x['settings']
        cloudflare_tags = x['tags']
        cloudflare_ttl = x['ttl']
        cloudflare_content = x['content']
        cloudflare_type = x['type']
        break
#print(cloudflare_name)
#print(cloudflare_proxied)
#print(cloudflare_settings)
#print(cloudflare_tags)
#print(cloudflare_ttl)
#print(cloudflare_content)
#print(cloudflare_type)
        
#print(cloudflareip)
#print(mainipstatus)

#verify the IP address in use
if(mainip == cloudflareip):
    if(mainipstatus=='UP'):
        siteip = cloudflareip
    else:
        siteip = secondaryip
elif(secondaryip == cloudflareip):
    if(mainipstatus!='UP' and secondaryipstatus=='UP'):
        siteip = cloudflareip
    else:
        siteip = mainip
else:
    print('no IP present')
    
#print(siteip + 'is the site IP')
#modify the Cloudflare IP of the record if the site ip and cloudflareip are not the same
if(siteip!=cloudflareip):
    cloudflare_url='https://api.cloudflare.com/client/v4/zones/zone-id/dns_records/'+cloudflarerecordid
    cloudflare_update = {
    'name' : cloudflare_name,
    'proxied' : cloudflare_proxied,
    'settings' : cloudflare_settings,
    'tags' : cloudflare_tags,
    'ttl' : cloudflare_ttl,
    'content' : siteip,
    'type' : cloudflare_type
    }
    cloudflare_response = requests.request("PATCH", cloudflare_url, headers=cloudflare_headers, data=json.dumps(cloudflare_update))
    #print(cloudflare_update)
    #cloudflare_response = requests.patch(cloudflare_url, headers=cloudflare_headers, data=cloudflare_update)
    cloudflare_response_json=json.loads(cloudflare_response.text)
    print(cloudflare_response_json)
else:
    print('same IP')