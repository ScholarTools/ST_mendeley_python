import requests
import wget
import zipfile
import os

# get the latest chrome driver version number
url = 'https://chromedriver.storage.googleapis.com/LATEST_RELEASE'
response = requests.get(url)
version_number = response.text
version_number = '79.0.3945.36'

# build the donwload url
download_url = "https://chromedriver.storage.googleapis.com/" + version_number + "/chromedriver_mac64.zip"

# download the zip file using the url built above
latest_driver_zip = wget.download(download_url,'chromedriver.zip')

# extract the zip file
with zipfile.ZipFile(latest_driver_zip, 'r') as zip_ref:
    zip_ref.extractall('/Users/jim/Box Sync') # you can specify the destination folder path here
# delete the zip file downloaded above
os.remove(latest_driver_zip)

from selenium import webdriver

os.chmod('/Users/jim/Box Sync/chromedriver',755)
driver = webdriver.Chrome(executable_path='/Users/jim/Box Sync/chromedriver')
