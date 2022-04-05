# -*- coding: utf-8 -*-
"""
This module is meant to handle things related to authentication for the
Mendeley API.

In general it is better to interact with the API directly, rather than
interacting with this module.

Mendeley Authethentication Documentation:
https://dev.mendeley.com/reference/topics/authorization_overview.html
https://dev.mendeley.com/reference/topics/authorization_auth_code.html

Public Methods
-----------------------------
retrieve_public_authorization()
retrieve_user_authorization()




config parameters:
    - default_save_path




"""
#Standard Library
from __future__ import print_function

import re
import random
import pickle
import os
import sys
import datetime


#Third Party
import requests
from requests.auth import AuthBase, HTTPBasicAuth
import pytz #This seems to be a 3rd party library but is installed on
#my local Python installation (Py Timze Zones)

#Local imports
from . import utils
from .utils import get_truncated_display_string as td
#from .utils import get_list_class_display as cld

#TODO: Why don't we use config_helpers?
from . import config
from . import errors


#Error definitions
#-------------------------------------
def _print_error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


"""
-------------------------------------------------------------------------------
These are methods that other modules might want to access directly.

"""

def retrieve_public_authorization(force_reload=False,verbose=False):
    """    
    Loads public credentials
    
    Parameters
    ----------
    force_reload : False
    verbose : False

    Returns:
    --------
    PublicCredentials    
    """
    if force_reload:
        return _PublicAuthorization()
    elif _PublicAuthorization.token_exists_on_disk():
        return _PublicAuthorization.load()
    else:
        return _PublicAuthorization()
        
def retrieve_user_authorization(user_name=None,
                                user_info=None,
                                session=None,
                                force_reload=False,
                                verbose=False):
    """
    
    Parameters
    ----------
    user_name : string
    user_info : 
    
    
    """
    if force_reload:
        return _UserAuthorization(user_name, user_info, session)
    elif _UserAuthorization.token_exists_on_disk(user_name,user_info):
        return _UserAuthorization.load(user_name, user_info, session)
    else:
        return _UserAuthorization(user_name, user_info, session)
        
"""
-------------------------------------------------------------------------------
"""

class _Authorization(AuthBase):
    
    """
    This is a superclass for:
        _UserAuthorization
        _PublicAuthorization
    
    TODO: I currently have a lot of duplicated code between the two classes 
    that needs to be moved to here.
    # - get_file_path()
    # - renew_token_if_necessary()
    
    Attributes
    ----------
    token_expired : 
    expires : timestamp
    session : requests.Session
    """
 
    """
    Abstract Methods
    ----------------
    renew_token
    
    """
    #The amount of time prior to token expiration that a request should be
    #made to renew the token. See self.renew_token_if_necessary()
    #I'm trying to avoid the following:
    # 1) check for valid token
    # 2) token becomes invalid
    # 3) request with invalid token
    #
    #Default value: check if there is less than 1 minute
    RENEW_TIME = datetime.timedelta(minutes=1) 
    
    AUTH_URL = 'https://api.mendeley.com/oauth/token'   
   
    @staticmethod
    def get_save_base_path(create_folder_if_no_exist=False):
        """
        The API credentials are stored at:
        <repo_base_path>/data/credentials
        
        NOTE: Anything in the data folder is omitted from versioning using
        .gitignore
        """
        
        if config.default_save_path is not None:        
            save_folder_path = os.path.join(config.default_save_path,'credentials')
            if create_folder_if_no_exist and not os.path.exists(save_folder_path):
                os.makedirs(save_folder_path)
            return save_folder_path
        else:
            return config.get_save_root(['credentials'],create_folder_if_no_exist)

    @property
    def token_expired(self):        
        """
        Determine if the token has expired. As of this writing
        the token expires 1 hour after being granted.
        """

        time_diff = self.expires - datetime.datetime.now(pytz.utc)
      
        return time_diff.total_seconds() < 0 
        
    def renew_token_if_necessary(self):
      
        """
        Renews the access token if it has expired or is about to expire.
        """
      
        if datetime.datetime.now(pytz.utc) + self.RENEW_TIME > self.expires:
            self.renew_token()
            
    def __call__(self,r):
        
        """
        This method is called before a request is sent.
        
        Parameters
        ----------
        r : Requests Object
        
        See Also
        --------
        .api.PublicMethods
        """
        #Called before request is sent
          
        self.renew_token_if_necessary()
        
        r.headers['Authorization'] =  "bearer " + self.access_token
        
        return r 
                
    @classmethod
    def get_file_path(cls,user_name,create_folder_if_no_exist = False):
        """     
        Provides a consistent path to where this object can be saved and loaded
        from.
        
        Parameters:
        -----------
        user_name: str
            See class initialization for definition.
        
        Returns:
        -------
        str
        
        """

        save_name = utils.user_name_to_file_name(user_name) + '.pickle'

        save_folder_path = cls.get_save_base_path(create_folder_if_no_exist)
        
        final_save_path  = os.path.join(save_folder_path,save_name)
        
        return final_save_path
        
    def populate_session(self,session=None):
        if session is None:
            self.session = requests.Session() 
        else:
            self.session = session
        
    def save(self):
        
        """
        Saves the class instance to disk.
        """
        save_path = self.get_file_path(self.user_name, create_folder_if_no_exist=True)
        with open(save_path, "wb") as f:
            pickle.dump(self,f)

class _PublicAuthorization(_Authorization):
    
    """
    TODO: Fill this out    
    
    """
        
    def __init__(self, session = None):
        self.user_name ='public'
        self.populate_session(session)
        temp_json = self.create_initial_token()
        self.init_json_attributes(temp_json)
        self.save()

    def create_initial_token(self):

        """
        Requests the client token from Mendeley. The results can then be
        used to construct OR update the object.
        
        See Also:
        ---------------
        get_public_credentials
        
        """
        URL = 'https://api-oauth2.mendeley.com/oauth/token'
  
        payload = {
            'grant_type'    : 'client_credentials',
            'scope'         : 'all',
            'redirect_uri'  : config.Oauth2Credentials.redirect_url,
            'client_secret' : config.Oauth2Credentials.client_secret,
            'client_id'     : config.Oauth2Credentials.client_id,
            }   
  
        r = requests.post(URL,data=payload)
        
        if r.status_code != requests.codes.ok:
            raise Exception('Request failed, TODO: Make error more explicit')
        
        return r.json()

    def init_json_attributes(self,json):
        self.access_token = json['access_token']
        self.token_type = json['token_type']
        self.expires = datetime.datetime.now(pytz.utc) + datetime.timedelta(seconds=json['expires_in'])
    
    def __repr__(self):
        pv = ['access_token',self.access_token,
              'token_type',self.token_type,
              'expires',str(self.expires),
              'token_expired',self.token_expired]
        return utils.property_values_to_string(pv)
                
    def renew_token(self):
        temp_json = self.create_initial_token()
        self.init_json_attributes(temp_json)
        self.save()

    @classmethod
    def token_exists_on_disk(cls):
        """
        For public use 'public'
        """
        load_path = cls.get_file_path('public')
        return os.path.isfile(load_path)
        
    @classmethod
    def load(cls,session=None):
        """
        Loads the class instance from disk.        
        
        """
   
        load_path = cls.get_file_path('public')
        
        if not os.path.isfile(load_path):
            raise Exception('Requested token does not exist')
                       
        with open(load_path,'rb') as f:
            self = pickle.load(f)
         
        self.populate_session(session)     
          
        return self 

class _UserAuthorization(_Authorization):
    
    """
    This class represents an access token (and refresh token). An access token 
    allows a program to access user specific information. 
    
    This class should normally be retrieved by:
    
        retrieve_user_authorization()
        
    This class relies on the user configuration.    
    
    Attributes
    ----------
    from_disk : bool
        Whether or not the class was instantiated from disk.
    version : string
        The current version of the access token. Since these are saved to disk
        this value is retained in case we need to make changes.
    user_name : string
    access_token : string
        The actual access token. This might be renamed ...
    token_type : str
        I'm not really sure what this is for. It is currently sent in response
        to a request for an access token but I'm not using it. Currently the 
        value is "bearer"
        
    """  

    
    def __init__(self, user_name=None, user_info=None, session = None):
        """
        Parameters
        ----------
        user_name : string
            Allows retrieval of the user's credential information based
            on an alias 
        user_info : UserInfo
        session : TODO: Is this even being used????
        
        Examples
        --------
        UserCredentials(session=my_session) #calls default user           
           
        """
        
        #Avoid storing in class (and thus avoid saving to disk)
        user_info = self.resolve_user_info(user_name,user_info)
        
        self.version = 1
        self.from_disk = False
        self.populate_session(session)
        self.user_name = user_info.user_name
        json = self.create_initial_token(user_info)
        
        self.init_json_attributes(json)
        self.save()
     
    def recreate_initial_token(self):
        """
        Sometimes the token becomes invalid. When this happens this code
        attempts to reobtain the initial token.
        """

        #TODO: Support prompting user if we can't find
        #the user name in the config file => presumably the user
        #used manual entry    
        
        user_info = self.resolve_user_info(self.user_name,None)
        json = self.create_initial_token(user_info)
        self.init_json_attributes(json)
        self.save()
      
     
    def create_initial_token(self,user_info):
        """
        
        json = self.create_initial_token(user_info)
        
        Parameters
        ----------
        user_info
        
        See Also
        --------
        .init_json_attributes   
        
        """
        temp = UserTokenRetriever(user_info=user_info,session=self.session)
        return temp.token_json
        
    def init_json_attributes(self, json):
        """
        Mendeley will return json from the http request.
        
        Ignoring token_type attribute (generally/always? with 'bearer' value)
        """
        self.access_token = json['access_token']
        self.token_type = json['token_type']
        self.refresh_token = json['refresh_token']
        self.expires = datetime.datetime.now(pytz.utc) + datetime.timedelta(seconds=json['expires_in'])
        
        return None

    def __repr__(self):
        pv = ['version',self.version,
              'user_name',self.user_name,
              'access_token',td(self.access_token),
              'token_type',self.token_type,
              'refresh_token',td(self.refresh_token),
              'expires',self.expires,
              'token_expired',self.token_expired]
        return utils.property_values_to_string(pv)

    @classmethod
    def token_exists_on_disk(cls,user_name=None,user_info=None):
        """
        """
        
        user_info = cls.resolve_user_info(user_name,user_info)
        load_path = cls.get_file_path(user_info.user_name)
        return os.path.isfile(load_path)
      
    @classmethod
    def resolve_user_info(cls,user_name,user_info):
        """
        Given default values of user_name and user_info, determine
        which one was a valid input (i.e. which was specified)
        
        Calling formats
        ----------------
        self.resolve_user_info(user_name,None)
        self.resolve_user_info(None,user_info)
        """
        
        if user_info is None:
            user_info = UserInfo.from_config(user_name)  
            
        return user_info
      
    def renew_token(self):     
        """
        Renews the access token so that requests can be made for user data.      
      
        NOTE: The refresh_token can be used even after the access token has 
        expired.
        """      
        
        client_auth = requests.auth.HTTPBasicAuth(
            config.Oauth2Credentials.client_id,
            config.Oauth2Credentials.client_secret)
        
        post_data = {"grant_type"   : "refresh_token",
                     "refresh_token": self.refresh_token,
                     "redirect_uri" : config.Oauth2Credentials.redirect_url}
       
        #TODO: We should replace this with the session object            
        r = requests.post(self.AUTH_URL, auth=client_auth, data=post_data)
      
        #Observed errors:
        #----------------------------------
        #1) {"error":"invalid_grant","error_description":"Invalid grant"}
        #
        # - Was fixed by deleting the pickled version of the credentials
        #
        #   401
        #   {"message":"Credentials are required to access this resource."}
        
        #http://dev.mendeley.com/reference/topics/authorization_auth_code.html
        #
        #Possible errors include (I think):
        # 1) invalid_request - values were missing in request
        # 2) unsupported_grant_type - when the grant type is not refresh_token 
        #   or authorization_code
        # 3) invalid_grant - values were invalid
        

        #TODO: rewrite based on switching on possible errors
        #e.g. if error
        #error_data = r.json()
        #error_type = error_data.get('error')
        #'invalid_grant'
        #'invalid_request'
        #'unsupported_grant_type'
        # => none of these
        #throw specific errors for each of these
        
        #Renewal code
        #---------------------------------------
        #create_initial_token(self,user_info):
        if r.status_code != requests.codes.ok:
            error_data = r.json()
            if error_data["error"] == "invalid_grant":
                self.recreate_initial_token()
                return
        
            #Currently non-fixable error
            _print_error("Error for user: ", self.user_name)
            
            if (self.from_disk):
                _print_error("Credentials loaded from:\n%s" % 
                             self.get_file_path(self.user_name))
                _print_error("------------------------------------------------")
                _print_error(r.text)
                _print_error("------------------------------------")
                #This assumes we are loading from disk ...
                _print_error("The current solution is to delete the"
                             " saved credentials")
                raise errors.AuthException('TODO: Fix me, request failed ...')
      
        self.init_json_attributes(r.json())      
        self.save()

    

        
    @classmethod
    def load(cls, user_name=None, user_info=None, session = None):
        
        """
        Loads the class instance from disk.        
        
        Parameters
        ----------
        user_name : string (default None)
            If the user_name is not passed in then a default user should be
            defined in the config file.
        """
        
        #TODO: This should eventually have version lookup
        #https://docs.python.org/2/library/pickle.html#pickling-and-unpickling-normal-class-instances
        #would involve using __setstate__
        
        user_info = cls.resolve_user_info(user_name,user_info)        
        
        load_path = cls.get_file_path(user_info.user_name)

        #Handle potentially missing file
        #-------------------------------
        if not os.path.isfile(load_path):
            raise Exception('Requested token does not exist')
                       
        with open(load_path,'rb') as f:
            #TODO: Try to do this then specify where we are loading from if this fails
            self = pickle.load(f)
        
        self.from_disk = True
        
        self.populate_session(session)
                          
        return self    

class UserTokenRetriever(object):
    
    #??? Why is this not underscore leading?
    #Eventually I want to make this public
    #   - Note, the user 
    
    """
    - Called by _UserAuthorization in create_initial_token
    - Manual call
        from mendeley import auth
        ut = auth.UserTokenRetriever()
    
    """
    
    
    """
        Rough OAUTH Outline
        -------------------
        1) User askes to use client (i.e. this code or an "app")
        2) Client gives User some information to give to Mendeley regarding
        the Client so that Mendeley can connnect the user to the Client.
        3) User gives the Client info to Mendeley along with user's id & pass, 
        and Mendeley gives the User some information (the authorization code) to 
        give to the Client.
        4) Client now has the information it needs to make requests for the 
        User's data. In most cases (although not this one) this would allow the
        User to never give it's Mendeley credentials to the client.
    """
    
    def __init__(self,user_info=None,session=None):
        """
        
        UserTokenRetriever(user_info,session)
        
        Parameters
        ----------
        user_info : UserInfo
        session : requests.Session
        """
        manual_approach = user_info is None

        if session is None:
            session = requests.Session()
            
        self.session = session
        
        #Authorization Token
        #---------------------------------
        BASE_AUTH_URL = "https://api.mendeley.com/oauth/authorize"
        ACCESS_TOKEN_URL = "https://api.mendeley.com/oauth/token"
        
        rand_state = random.random()
        payload = {
            'client_id'     : config.Oauth2Credentials.client_id,
            'redirect_uri'  : config.Oauth2Credentials.redirect_url,
            'response_type' : 'code',
            'scope'         : 'all',
            'state'         : rand_state}
                
        req = requests.Request('GET', BASE_AUTH_URL, params=payload)
        prepped = self.session.prepare_request(req)
        
        auth_url = prepped.url
        
        if manual_approach:
            print("Navigate to the following address, follow prompts:")
            print(auth_url)
            current_url = input("What's the final url?")
        else:
            current_url  = self.get_authorization_code_auto(auth_url,user_info)
        
        x = re.findall("\?code=([^&]+)",current_url)
        code = x[0]
        
        self.token_json = self.trade_code_for_user_access_token(code,ACCESS_TOKEN_URL)

    def get_authorization_code_auto(self,auth_url,user_info):  
        """
        The authorization code is what the user gives to the Client, allowing
        the Client to make requests on behalf of the User to Mendeley
    

        
        """    
        HEADLESS_BROWSER = True
        
        from selenium import webdriver
        
        #This registers chromedriver to the path
        import chromedriver_binary # pylint: disable=unused-import
        #python-chromedriver in anaconda
        
        USER_EMAIL = user_info.user_name
        USER_PASS = user_info.password
        if HEADLESS_BROWSER:
            options = webdriver.ChromeOptions()
            options.add_argument('headless')
            browser = webdriver.Chrome(chrome_options=options)
        else:
            browser = webdriver.Chrome()
        
        #first page - submit user name    
        browser.get(auth_url)
        elem = browser.find_element_by_id("bdd-email")
        elem.send_keys(USER_EMAIL)
        submit_button = browser.find_element_by_id("bdd-elsPrimaryBtn")
        submit_button.click()
        
        #next page - submit password
        #--------------------------------------
        elem = browser.find_element_by_id("bdd-password")
        elem.send_keys(USER_PASS)
        submit_button = browser.find_element_by_id("bdd-elsPrimaryBtn")
        submit_button.click()
                
        current_url = browser.current_url
        if not current_url.startswith("https://localhost"):
            submit_button = browser.find_element_by_class_name("button-primary")
            submit_button.click()
            current_url = browser.current_url
         
        browser.close()
            

        
        return current_url
        
        """
        #This is a complete asdlkklfsajdfksjd mess
        #----------------------------------------------------------------------
        #
        #   I couldn't get the submission of the email to work, I have  no
        #   idea where the mismatch is between my code and what I'm seeing
        #   in the browser
        #
        #   
        
        #Beautiful Soup requirement - we could consider Selenium ...
        import bs4 as bs

        
        
        
        rand_state = random.random()
        
        #Note this pipeline currently assumes the user is not signed in
        #via the session.
        
        #STEP 1: Get signin form
        #----------------------------------------------
        payload = {
            'client_id'     : config.Oauth2Credentials.client_id,
            'redirect_uri'  : config.Oauth2Credentials.redirect_url,
            'response_type' : 'code',
            'scope'         : 'all',
            'state'         : rand_state}
        
        r = self.session.get(URL, params=payload)
        
        #r = self.session.get(URL, params=payload,
        #                     proxies={"http": "http://127.0.0.1:8888", "https":"http:127.0.0.1:8888"},verify=False)

        # TODO: build in check for invalid redirect URI
        # Can change redirect URI above
        #
        if r.status_code != requests.codes.ok:
            #An invalid request was made by a third-party app
            #
            #   The app wasn;t registerd ...???
            
            #import pdb
            #pdb.set_trace()
            raise Exception('App authorization request failed at step 1')
         

               
        #STEP 2: Enter email
        #------------------------------------------------------
        soup = bs.BeautifulSoup(r.text,'lxml')
        
        forms = soup.find_all('form')
        form2 = forms[1]
        URL2 = "https://id.elsvier.com" + form2['action']
        
        payload2 = {
            'pf.username' : self.user_info.user_name,
            'action' : 'emailContinue'}
        
        import pdb
        pdb.set_trace()
        
        r2 = self.session.post(URL2,data=payload2,allow_redirects=True,
                               headers={'DNT':'1','User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0',
                                        'referer': r.url,'Origin':'https://id.elsevier.com','Host':'id.elsevier.com'})
        
        #r2 = self.session.post(URL2,data=payload2,allow_redirects=True,
        #                       headers={'DNT':'1','User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0','referer': r.url,'Origin':'https://id.elsevier.com','Host':'id.elsevier.com'},
        #                       proxies={"http": "http://127.0.0.1:8888", "https":"http:127.0.0.1:8888"},verify=False)
        
        if r2.status_code != requests.codes.ok:
            raise Exception('App authorization request failed at step 2')
        
        #STEP 3: Enter Password
        #-------------------------------------------------------
        
        import pdb
        pdb.set_trace()
        
        #password=1234asdf&rememberme=on&action=signin

        
        payload3 = {
            'password' : self.user_info.password,
            'action' : 'signin'}
        r3 = self.session.post(r2.url,data=payload3,allow_redirects=True)  
        
        import pdb
        pdb.set_trace()
        
        payload4 = {
            'response_type' : 'code',
            'client_id'     : config.Oauth2Credentials.client_id,
            'scope'         : 'all',
            'redirect_uri'  : config.Oauth2Credentials.redirect_url,
            'state'         : rand_state,
            'authorized'    : 'true'}
        
        r4 = self.session.post(r3.url,data=payload4,allow_redirects=True)  
        
        
        
        import pdb
        pdb.set_trace()
        
        query = requests.utils.urlparse(r4.url).query
        params = dict(x.split('=') for x in query.split('&'))
        #https://localhost/?code=JNTH6janlZskdM2Re3TUWVgIE5I&state=0.23650318353
        #https://localhost/?error=access_denied&error_description=User+denied+the+request&state=0.23650318353       
        
        if r2.status_code != 302:
            #TODO: Look for 200 with Incorrect details
            #<p class="alert alert-error">\n    Incorrect details. <a target="_blank" href="http://www.mendeley.com/forgot/">Forgot your password?</a>
            
            #1) I've gotten a 200 ok with "Incorrect Details" which just
            #turned out that I needed to login to Mendeley first to finish
            #registration
            print(self.user_info)
            print(r2.status_code)
            print(r2.text)
            raise Exception("Auto-submission of the user's credentials failed")  
        
        #STEP 3: Grab code from redirect URL
        #----------------------------------------------
        parsed_url = requests.utils.urlparse(r2.headers['location'])
        
        #TODO: Update with response from StackOverflow    
        #instead of blindly grabbing the query
        #query => 'code=value'
        authorization_code = parsed_url.query[5:]
        
        return authorization_code
        """

    def trade_code_for_user_access_token(self,code,access_token_url):
             
        """
        This method asks Mendeley for an access token given a user's 
        authentication code. This code comes from the user telling 
        Mendeley that this client (identified by a Client ID) has permission 
        to get information from the user's account.
        
        Parameters:
        -----------
        user: UserInfo
            This contains informaton about the user and can be obtained from:
            request_authorization_code.
    
        Returns:
        --------
        UserCredentials
            This token can be used to request information from the user's account.
            
        See Also:
        ---------
            
        
        """        
        #headers = {'content-type': 'application/x-www-form-urlencoded'}
        
        payload = {
            'grant_type'    : 'authorization_code',
            'code'          : code,
            'redirect_uri'  : config.Oauth2Credentials.redirect_url
            } 
    
        username = config.Oauth2Credentials.client_id
        password = config.Oauth2Credentials.client_secret
        r = self.session.post(access_token_url,
                              data=payload,
                              auth=HTTPBasicAuth(username,password))
    
        if r.status_code != requests.codes.ok:
            raise Exception('Error requesting initial access token')    
        
        return r.json()
            
class UserInfo(object):
    
    """
    This is a small little class that stores user info. The irony of such a
    class, one that holds onto the users password, given the goals OAuth,
    is not lost on me.    
    
    This class might be removed in favor of only using the authorization code.
    
    Previously I had used the profile methods to get a unique id but it seems
    like that function has changed :/ The use case I have in mind is someone
    that manually provides an authorization code. It would be nice to be able
    to automatically pull their information given this code, rather than
    have them provide it as well.
    
    Attributes
    ----------
    user_name : string
        The user_name is actually an email address.
    password : str
        The user's password.
        
    type : string
        - 'user input'
        - 'default'
        - 'other user'
    from_config : boolean
     
    
    """
    def __init__(self,user_name,password):
        self.user_name = user_name
        self.password = password
        self.type = 'user input'
        self.from_config = False
    
    @classmethod
    def from_config(cls,user_name=None):

        self = cls.__new__(cls)

        user = config.get_user(user_name)
        
        self.user_name = user.user_name
        self.password = user.password
        if user_name is None:
            self.type = 'default'
        else:
            self.type = 'other user'
            
            
        self.from_config = True    
            
        return self


    def __repr__(self):
        pv = ['user_name',self.user_name,
              'password',self.password,
              'type',self.type,
              'from_config',self.from_config]
        return utils.property_values_to_string(pv)



  
