# -*- coding: utf-8 -*-
"""
The configuration is a user specified file. This module works with those
user specified files.

See Also
--------


"""

#Standard Library Imports
import sys
import os
import importlib.machinery #Python 3.3+

#Local Imports
#---------------------------------------------------------
from . import errors

def _print_error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs) 

# Can't use utils in this module - circular imports
#from . import utils
#from mendeley.errors import InvalidConfig

try:
    from . import user_config as config
except ImportError:
    _print_error("----------------   User Config Info  ----------------")
    _print_error("Copy config_template.py to user_config.py")
    _print_error("Edit as necessary")
    _print_error("------------------------------------")   
    raise errors.InvalidConfig('user_config.py not found')
        
#config_location redirection if necessary
#-------------------------------------------------      
if hasattr(config,'config_location'):
    #In this case the config is really only a pointer to another config  
    config_location = config.config_location
    
    if not os.path.exists(config_location):
        raise errors.InvalidConfig('Specified configuration path does not exist')
    
    loader = importlib.machinery.SourceFileLoader('config', config_location)    
    config = loader.load_module()
    
#-----------------------------------------------------------------

class Config(object):
    
    """
    Attributes
    ----------
    Oauth2Credentials : 
    default_user
    default_save_path : 
    other_users : User
    
    """
    
    def __init__(self):
        
        #This initialization code also defines what we are looking for or 
        #not looking for
        if not hasattr(config,'Oauth2Credentials'):
            raise errors.InvalidConfig('user_config.py requires a "Oauth2Credentials" class')
        
        self.Oauth2Credentials = config.Oauth2Credentials        
        
        if hasattr(config,'DefaultUser'):       
            self.default_user = User(config.DefaultUser)
            
        if hasattr(config,'default_save_path'):
            self.default_save_path = config.default_save_path
        
        if hasattr(config,'other_users'):
            self.other_users = config.other_users

        self.validate()
    
    def get_user(self,user_name):
        """
        Calling Forms
        -------------
        1) Returns default user
        self.get_user(None)
        
        2) Returns default user
        self.get_user("default")

        3) Returns user if specs can be found
        self.get_user(user_name)
        
        Returns
        -------
        User

        """

        if user_name is None:
            return self.default_user
        
        if user_name == 'default':
            return self.default_user
            
        #If the user name requested is the default user's name
        #then return the default user
        #
        #This was created for recreating auth tokens when the name is known
        #rather than only knowing 'default'
        #- i.e. if the 'default' user is 'Jim' then if we request 'Jim'
        #	  in this function then we need to be able to get the default 
        #  user credentials
        if self.default_user.user_name == user_name:
            return self.default_user
         
        #If the default fails, fall back to other_users    
        if not hasattr(self,'other_users'):
            raise errors.InvalidConfig(
                    'Missing user and other_users is not specified in the config file')
            
        other_users = self.other_users
        
        if user_name not in other_users:
            raise errors.InvalidConfig(
                    'other_users config parameter is missing the requested user name')
            
        user_data = other_users[user_name]
        
        return User(user_data)
    
    @property
    def has_default_user(self):
        return hasattr(config,'DefaultUser')
    
    @property
    def has_testing_user(self):
        if not hasattr(config,'other_users'):
            return False
        else:
            #Keys are aliases for the users accounts (others_users should be a dict)
            return 'testing' in config.other_users

    def validate(self):
        #Oauth2Credentials validation
        #----------------------------------------------------    

    
        auth_creds = self.Oauth2Credentials
        _ensure_present_and_not_empty(auth_creds,'Oauth2Credentials','client_secret')
        _ensure_present_and_not_empty(auth_creds,'Oauth2Credentials','client_id')
        _ensure_present_and_not_empty(auth_creds,'Oauth2Credentials','redirect_url')
        #TODO: can check that redirect url is valid    
        
        #   Optional Values
        #==========================================================================
        
        #   DefaultUser validation
        if hasattr(self,'DefaultUser'):
            du = self.DefaultUser
            _ensure_present_and_not_empty(du,'DefaultUser','user_name')
            #TODO: Could check for an email (i.e. user name is typically an email)        
            _ensure_present_and_not_empty(du,'DefaultUser','password')   
    
        #   default_save_path validation
        if hasattr(config,'default_save_path'):
            pass
            #TODO: Validate that the path exists

        self.Oauth2Credentials = config.Oauth2Credentials        
        
        if hasattr(config,'DefaultUser'):       
            self.default_user = User(config.DefaultUser)
            
        if hasattr(config,'default_save_path'):
            self.default_save_path = config.default_save_path
        else:
            self.default_save_path = None
        
        if hasattr(config,'other_users'):
            self.other_users = config.other_users

	# TODO: rewrite without using utils
    # Utils currently calls back into this class
    # so we want to avoid circular dependencies ...
    '''
    def __repr__(self):
        pv = ['Oauth2Credentials', cld(self.Oauth2Credentials), 
              'default_user', cld(getattr(self,'default_user',None)),
                'default_save_path',getattr(self,'default_save_path',None),
                'other_users',cld(getattr(self,'other_users',None))]
        return utils.property_values_to_string(pv)
    '''


def _ensure_present_and_not_empty(obj_or_dict,name,key_or_attribute,none_is_ok=False):
    
    """
    Inputs
    ------
    obj_or_dict : object instance or dict
    name : string
        The name of the object or dict, for displaying if an error occurs
    key_or_attribute : string
        The entry in the object or dict to examine
    none_is_ok : bool (default False)
        If true a None value for the entry is ok
    """    
    
    if isinstance(obj_or_dict,dict):
        if key_or_attribute in obj_or_dict:
            value = obj_or_dict[key_or_attribute]
        else:
            raise errors.InvalidConfig('%s is missing the entry %s, please fix the config file' % (name,key_or_attribute))
    else:
        if hasattr(obj_or_dict,key_or_attribute):
            value = getattr(obj_or_dict,key_or_attribute)
        else:
            raise errors.InvalidConfig('%s is missing the entry %s, please fix the config file' % (name,key_or_attribute))
            
    
    if value is None:
        if none_is_ok:
            pass
        else:
            raise errors.InvalidConfig('"%s" in %s was found to have none value which is not allowed, please fix the config file' % (key_or_attribute,name))
    elif len(value) == 0:
        raise errors.InvalidConfig('"%s" in %s was found to be empty and needs to be filled in, please fix the config file' % (key_or_attribute,name))

class User(object):
    
    def __init__(self,config_default_user):
        """
            Inputs
            ------
            config_default_user : class
                Should have the following properties
                    .user_name
                    .password
            
            #TODO: Allow variations on the User formats
            #e.g => (user_name,password) or list
            #e.g => JSON or YAML            
        """
    
        #if isinstance(config_default_user,dict):
        #   
        #
    
        self.user_name = config_default_user.user_name
        self.password = config_default_user.password
