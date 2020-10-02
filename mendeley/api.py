# -*- coding: utf-8 -*-
"""
This module is meant to implement all functions described at:

    #1) http://dev.mendeley.com/methods/
    #
    #   Shows request parameters a bit more clearly    
    
    #2) https://api.mendeley.com/apidocs/
    #
    #   Testing interface, nicer organization
    

General Usage
-------------
from mendeley import API
user_api = API()
public_api = API()


Request Options
---------------
In addition to the options of a given function, the following options are also
supported:

    TODO: fill this in: example _return_type

TODO: Create an options class that can be given to the request (e.g. for return type)

Method Types (from Mendeley)
----------------------------
Annotations
Academic Statuses
Catalog Documents
Catalog Search
Datasets
Disciplines
Documents
Documents Metadata Lookup
Files
File Content
Folders
Groups
Identifier Types
Locations
Profiles
Trash
Errors

"""

#Standard Library
from typing import Optional, Union, TypeVar, List
import sys
import mimetypes
from os.path import basename
from datetime import datetime
import json

#Third party
import requests
from requests import ConnectionError

#Local Imports
from . import auth
from . import models
from . import utils
#from . import user_config
from .utils import get_truncated_display_string as td
from .utils import get_list_class_display as cld

from . import errors

DST = Union[str,datetime,None]

PY2 = int(sys.version[0]) == 2

if PY2:
    from urllib import quote as urllib_quote
else:
    from urllib.parse import quote as urllib_quote

BASE_URL = "https://api.mendeley.com"
STR_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# For each view, specify which object type should be returned
catalog_fcns = {None: models.CatalogDocument,
                'bib': models.BibCatalogDocument,
                'stats': models.StatsCatalogDocument,
                'client': models.ClientCatalogDocument,
                'all': models.AllCatalogDocument
                }

document_fcns = {None: models.Document,
                 'bib': models.BibDocument,
                 'client': models.ClientDocument,
                 'tags': models.TagsDocument,
                 'patent': models.PatentDocument,
                 'all': models.AllDocument,
                 'deleted': models.DeletedDocument,
			     'ids': models.get_ids_only,
                 'json': models.get_json_only
                 }

def _print_error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs) 

#==============================================================================
class API(object):

    annotations : 'Annotations'
    definitions : 'Definitions'
    documents : 'Documents'
    files : 'Files'
    folders : 'Folders'
    trash : 'Trash'

    verbose : bool
    default_return_type : str

    #TODO: These types are not correct ...
    #_UserAuthorization
    access_token : str
    last_url : str
    # TODO: This isn't correct
    last_response : str
    # TODO: This isn't correct
    last_params : str

    """
    
    Attributes
    ----------
    default_return_type : {'object','json','raw','response'}
        This is the default type to return from methods.
        'object' - returns a processed object
        'json' - returns the respone parsed as json
        'raw' - returns the response text without processing 
        'response' - returns the response object (requests library)
    verbose : bool (default False)
        
    last_response : 
    last_params : 
        
    """

    def __init__(self,
                 user_name=None,
                 verbose=False,
                 force_reload_auth=False,
                 default_return_type='object'):
        """
        Parameters
        ----------
        user_name : str (default None)
            - None : then the default user is loaded via config.DefaultUser
            - 'public' : then the public API is accessed
        verbose : str
        force_reload_auth : bool (default False)
            If true, the authorization is recomputed even if it hasn't expired.
        default_return_type : {'object','json','raw','response'}
        
        """

        self.verbose=verbose

        self.s = requests.Session()
        if user_name == 'public':
            self.public_only = True
            token = auth.retrieve_public_authorization(force_reload=force_reload_auth)
            self.user_name = 'public'
        else:
            self.public_only = False
            token = auth.retrieve_user_authorization(user_name, session=self.s,
                                                     force_reload=force_reload_auth)
            self.user_name = token.user_name

        self.default_return_type = default_return_type

        self.access_token = token
        self.last_url = None
        self.last_response = None
        self.last_params = None
        self.last_response_params = None
        self.last_object_fh = None
        self.last_return_type = None
        self.last_headers = None


        #TODO: Eventually I'd like to trim this based on user vs public
        self.annotations = Annotations(self)
        self.definitions = Definitions(self)
        self.documents = Documents(self)
        self.files = Files(self)
        self.folders = Folders(self)
        self.trash = Trash(self)

    def convert_datetime_to_string(self,dt):
        #TODO: make format string a module variable
        return dt.strftime(STR_FORMAT)

    @property
    def has_first_link(self):
        lr = self.last_response
        return hasattr(lr,'links') and 'first' in lr.links

    @property
    def has_next_link(self):
        lr = self.last_response
        return hasattr(lr,'links') and 'next' in lr.links

    def next(self):

        if not self.has_next_link:
            raise Exception('Next page does not exist')

        next_url = self.last_response.links['next']['url']
        params = {'return_type':self.last_return_type}
        return self.make_get_request(next_url,
                                     self.last_object_fh,
                                     params,
                                     self.last_response_params,
                                     self.last_headers)

    @property
    def has_prev_link(self):
        lr = self.last_response
        return hasattr(lr,'links') and 'prev' in lr.links

    def prev(self):

        if not self.has_prev_link:
            raise Exception('Next page does not exist')

        prev_url = self.last_response.links['prev']['url']
        params = {'return_type': self.last_return_type}
        return self.make_get_request(prev_url,
                                     self.last_object_fh,
                                     params,
                                     self.last_response_params,
                                     self.last_headers)


    @property
    def has_last_link(self):
        lr = self.last_response
        return hasattr(lr,'links') and 'last' in lr.links

    def __repr__(self):
        pv = [
            'last_url',self.last_url,
            'last_response',self.last_response,
            'last_params',td(self.last_params),
            'public_only', self.public_only, 
            'user_name', self.user_name,
            'has_first_link',self.has_first_link,
            'has_next_link',self.has_next_link,
            'has_prev_link', self.has_prev_link,
            'has_last_link', self.has_last_link,
            '---','--- method props ---',
            'annotations',cld(self.annotations),
            'definitions',cld(self.definitions),
            '---','--- internal ---',
            'access_token',cld(self.access_token),
            ]
        return utils.property_values_to_string(pv)

    def make_post_request(self,
                          url,
                          object_fh,
                          params,
                          response_params=None,
                          headers=None,
                          files=None):

        """
        Parameters
        ----------
        params : dict
            These are the parameters of the post request
        response_params :
            Parameters that are passed to the response object
            TODO: What are these?????
        headers :


        """
        #
        # http://docs.python-requests.org/en/latest/user/advanced/#streaming-uploads

        if params is not None:
            return_type = params.pop('return_type', self.default_return_type)
        else:
            return_type = self.default_return_type

        if files is None:
            params = json.dumps(params)

        #TODO: Why is this not like GET with a possible connection error?
        response = self.s.post(url, data=params, auth=self.access_token,
                               headers=headers, files=files)

        self.last_url = url
        self.last_response = response
        self.last_params = params
        self.last_object_fh = object_fh
        self.last_return_type = return_type
        self.last_headers = headers

        if not response.ok:
            print(response.text)
            print('')
            raise errors.CallFailedException('Call failed with status: %d' 
                                                % (response.status_code))

        return self.handle_return(response, return_type, response_params, object_fh)

    def make_get_request(self,
                         url,
                         object_fh,
                         params,
                         response_params=None,
                         headers=None):
        """
        
        Make a GET request to the server and return the response.

        Parameters
        ----------
        url : str
            URL to make request from.
        object_fh: function handle
            This is the object to instantiate and return to the user
        params : dict (default {})
            Dictionary of parameters to place in the GET query. Values may be
            numbers or strings.
        return_type : {'object','json','raw','response'}
            object - indicates that the result class object should be created.
                This is the slowest option but provides the most functionality.
            json   - 
            
        See Also:
        ---------
        .auth.UserCredentials.__call__()
        .auth.PublicCredentials.__call__()
        """

        # TODO: extract good_status = 200

        if params is None:
            params = {}
        else:
            if PY2:
                params = dict((k, v) for k, v in params.iteritems() if v)
            else:
                params = dict((k, v) for k, v in params.items() if v)

        return_type = params.pop('return_type', self.default_return_type)

        # NOTE: We make authorization go through the access token. The request
        # will call the access_token prior to sending the request. Specifically
        # the __call__ method is called.
        try:
            resp = self.s.get(url, params=params, auth=self.access_token, 
                              headers=headers)
        except ConnectionError:
            raise Exception('Failed to connect to the server, this usually'
                            'happens if there is no internet connection')

        self.last_url = url
        self.last_response = resp
        self.last_params = params
        self.last_response_params = response_params
        self.last_object_fh = object_fh
        self.last_return_type = return_type
        self.last_headers = headers

        if not resp.ok:
            _print_error("----------------   Error Details   ----------------")
            _print_error("Mendeley API Get Requested Failed")
            _print_error("Url: %s" % url)
            _print_error("Raw Response:")
            _print_error(resp.text)
            _print_error("------------------------------------")            
           
            raise Exception('Call failed with status: %d, see above for details' % (resp.status_code))

        return self.handle_return(resp, return_type, response_params, object_fh)

    def make_patch_request(self, url, object_fh, params, response_params=None, headers=None, files=None):
        #
        # http://docs.python-requests.org/en/latest/user/advanced/#streaming-uploads

        if params is not None:
            return_type = params.pop('return_type', self.default_return_type)
        else:
            return_type = self.default_return_type

        if files is None:
            params = json.dumps(params)

        resp = self.s.patch(url, data=params, auth=self.access_token,
                            headers=headers, files=files)

        self.last_url = url
        self.last_response = resp
        self.last_params = params
        self.last_object_fh = object_fh
        self.last_return_type = return_type
        self.last_headers = headers

        if not resp.ok:
            # if r.status_code != good_status:
            print(resp.text)
            print('')
            # TODO: This should be improved
            raise Exception('Call failed with status: %d' % (resp.status_code))

        return self.handle_return(resp, return_type, response_params, object_fh)

    def handle_return(self, req, return_type, response_params, object_fh):
        """
        This should only occur after the calling function has verified
        that no error was returned from the server.
        """
        if return_type is 'object':
            if response_params is None:
                return object_fh(req.json(), self)
            else:
                return object_fh(req.json(), self, response_params)
        elif return_type is 'json':
            return req.json()
        elif return_type is 'raw':
            return req.text
        elif return_type is 'response':
            return req
        elif return_type is 'ids':
            temp = req.json()
            return [x['id'] for x in temp]
        else:
            raise Exception('No match found for return type')

    def catalog(self, **kwargs):

        """
        
        TODO: This should probably be moved ...        
        
        Parameters
        ----------
        arxiv
        doi
        isbn
        issn
        pmid
        scopus
        filehash
        view
         - bib
         - stats
         - client - this option doesn't make much sense
         - all
        id : string
            Short for Catalog ID. Mendeley's catalog id. The only way I know of
            getting this is from a previous Mendeley search.
        
        Examples
        --------
        from mendeley import API
        m = API()
        c = m.catalog(pmid='11826063')
        c = m.catalog(pmid='11826063',view='bib')
        c = m.catalog(cid='f631d7ed-9926-34ed-b56e-0f5bb236b87b')
        """

        """
        Internal Note: Returns a list of catalog entries that match a 
        given query 
        #TODO: Is this the case for a given id? NO - only returns signle entry
        #TODO: Build this into tests
        """

        url = BASE_URL + '/catalog'
        if 'id' in kwargs:
            id = kwargs.pop('id')
            url += '/%s/' % id

        view = kwargs.get('view')
        response_params = {'fcn': catalog_fcns[view]}

        return self.make_get_request(url, models.DocumentSet.create, kwargs, response_params)


class Annotations(object):
    
    def __init__(self, parent):
        self.parent = parent
        self.url = BASE_URL + '/annotations'

    def get(self, document_id=None):
        """
        https://api.mendeley.com/apidocs#!/annotations/getAnnotations
        """

        if document_id is None:
            raise LookupError('Must enter a document ID to retrieve annotations.')

        params = dict()
        params['document_id'] = document_id
        params['include_trashed'] = False

        headers = {'Content-Type' : 'application/vnd.mendeley-annotation.1+json'}

        # return self.parent.make_get_request(url, models.Annotation, params, headers=headers)
        resp = requests.get(self.url, params=params, headers=headers, auth=self.parent.access_token)
        if resp.status_code != 200:
            return []
        else:
            return resp.text

    def create(self, annotation_body):
        """
        https://api.mendeley.com/apidocs/docs#!/annotations/createAnnotation
        """
        params = {'body': annotation_body}
        headers = {'Content-Type': 'application/vnd.mendeley-annotation.1+json'}

        resp = requests.post(self.url, params=params, headers=headers, auth=self.parent.access_token)
        if not resp.ok:
            raise ConnectionError(resp.status_code)


    def delete(self, **kwargs):
        url = BASE_URL + '/annotations'


        headers = {'Content-Type' : 'application/vnd.mendeley-folder.1+json'}
        pass

class Definitions(object):
    """
    TODO: These values should presumably only be queried once ...
    """

    def __init__(self, parent):
        self.parent = parent

    def academic_statuses(self, **kwargs):
        """
        
        https://api.mendeley.com/apidocs#!/academic_statuses/get
        
        Example
        -------        
        from mendeley import API
        m = API()
        a_status = m.definitions.academic_statuses()
        """
        url = BASE_URL + '/academic_statuses'

        return self.parent.make_get_request(url, models.academic_statuses, kwargs)

    def subject_areas(self, **kwargs):
        """
        
        https://api.mendeley.com/apidocs/docs#!/subject_areas/getSubjectAreas
        
        Examples
        --------
        from mendeley import API
        m = API()
        d = m.definitions.disciplines()
        
        TODO: Missing assignable
        
        """
        url = BASE_URL + '/subject_areas'

        return self.parent.make_get_request(url, models.subject_areas, kwargs)

    def document_types(self, **kwargs):
        """
        
        https://api.mendeley.com/apidocs#!/document_types/getAllDocumentTypes
        
        Examples
        --------
        from mendeley import API
        m = API()
        d = m.definitions.document_types()
        """
        url = BASE_URL + '/document_types'

        return self.parent.make_get_request(url, models.document_types, kwargs)

class Documents(object):
    def __init__(self, parent):
        self.parent = parent

    def get(self,
            return_type: Optional[str]=None,
            authored: Optional[bool]=None,
            folder_id: Optional[str]=None,
            group_id: Optional[str]=None,
            include_trashed: Optional[bool]=None,
            limit: Optional[int]=20,
            modified_since: DST=None,
            order: Optional[str]=None,
            profile_id: Optional[str]=None,
            sort: Optional[str]=None,
            starred: Optional[bool]=None,
            tag: Union[List[str],str,None] = None,
            view: Optional[str] = None):
        """
        https://api.mendeley.com/apidocs#!/documents/getDocuments

        Parameters
        ----------
        authored : logical
            TODO
        group_id : string
            The id of the group that the document belongs to. If not supplied 
            returns users documents.
        modified_since : string or datetime
            Returns only documents modified since this timestamp. Should be 
            supplied in ISO 8601 format.
        profile_id : string
            The id of the profile that the document belongs to, that does not 
            belong to any group. If not supplied returns users documents.
        
        starred : 
        limit : string or int (default 20)
            Largest allowable value is 500. 
            
             *** This is really the page limit since the iterator will 
	            allow exceeding this value.
	             
	         If 0 then everything is returned. 
	         
        order :
            - 'asc' - sort the field in ascending order
            ' 'desc' - sort the field in descending order            
        view : 
            - 'bib'
            - 'client'
            - 'tags' : returns user's tags
            - 'patent'
            - 'all'
            - 'ids' : only get ids
        sort : string
            Field to sort on. Avaiable options:
            - 'created'
            - 'last_modified'
            - 'title'

        Deleted Files
        -------------
        The underlying API has the same REST point for deleted files, but only
        returns the IDs of the deleted files. I've moved a request for deleted
        files to a different method.

        Examples
        --------
        from mendeley import API
        m = API()
        d = m.documents.get(limit=1)
        
        """

        url = BASE_URL + '/documents'

        d = dict()
        if return_type and return_type is not None:
            d['return_type'] = return_type
        if authored and authored is not None:
            d['authored'] = authored
        if folder_id and folder_id is not None:
            d['folder_id'] = folder_id
        if group_id and group_id is not None:
            d['group_id'] = group_id
        if include_trashed and include_trashed is not None:
            d['include_trashed'] = include_trashed
        if limit and limit is not None:
            if limit == 0:
                #0 is code for get all
                #we'll max out our per request size
                #then merge below
                d['limit'] = 500
            else:
                d['limit'] = limit
        if modified_since and modified_since is not None:
            d['modified_since'] = modified_since
            convert_datetime_to_string(d, 'modified_since')
        if order and order is not None:
            d['order'] = order
        if profile_id and profile_id is not None:
            d['profile_id'] = profile_id
        if sort and sort is not None:
            d['sort'] = sort
        if starred and starred is not None:
            d['starred'] = starred
        if tag and tag is not None:
            d['tag'] = tag

        response_doc_fcn = document_fcns[view]
        response_view = view

        if view is None:
            # If no view specified, set default to 'all'
            d['view'] = 'all'
            response_view = 'all'
        elif view == 'ids':
            #No view, default of None is ok
            #i.e. no assignment made to d[]
            pass
        else:
            d['view'] = view

        #Most of these are reference only, except for the fcn value
        response_params = {
            'fcn': response_doc_fcn,
            'view': response_view,
            'limit': limit,
            'page_id':0
            }

        verbose = _process_verbose(self.parent,d,response_params)
        if verbose:
            if limit == 0:
                print("Requesting all documents from Mendeley with params: %s" % (d))
            else:
                print("Requesting up to %d documents from Mendeley with params: %s" % (limit, d))
  
        result = self.parent.make_get_request(url, models.DocumentSet.create, d, response_params)

        if limit == 0:
            #TODO: Test this when the return type is not an object ...
            result.get_all_docs()       
        
        return result

    def get_by_id(self,
                   id: str,
                   return_type: Optional[str] = None,
                   view: Optional[str] = None):
        """
        https://api.mendeley.com/apidocs/docs#!/documents/getDocument

        Parameters
        ----------
        id :

        return_type : {'object','json','raw','response'}
            - 'object'
            - 'json'
            - 'raw'
            - 'response'

        view :
            - 'all'
            - 'bib'
            - 'client'
            - 'patent'
            - 'tags' : returns user's tags


        Examples
        --------
        from mendeley import API
        m = API()
        #Note you'd need to have this from a previous call ...
        id = 'b2ad49aa-4c99-3b04-85b3-b7e67245d5f2'
        d = m.documents.get_by_id(id)

        """

        url = BASE_URL + '/documents'
        url += '/%s/' % id

        d = dict()
        if return_type and return_type is not None:
            d['return_type'] = return_type

        response_params = {
            'fcn': document_fcns[view],
            'view': view,
            'limit': 1}

        return self.parent.make_get_request(url, models.DocumentSet.create, kwargs, response_params)

    def get_deleted(self,
            limit: Optional[int] = 20,
            return_type: Optional[str] = None,
            since: DST=None):
        """
        Parameters
        ----------
        limit
        return_type : Not Yet Implemented ...
        since
        group_id
        
        
        """

        url = BASE_URL + '/documents'

        d = dict()
        if return_type and return_type is not None:
            d['return_type'] = return_type
        if limit and limit is not None:
            if limit == 0:
                #0 is code for get all
                #we'll max out our per request size
                #then merge below
                d['limit'] = 500
            else:
                d['limit'] = limit


        if since and since is not None:
            d['deleted_since'] = since
            convert_datetime_to_string(d, 'deleted_since')
        else:
            d['deleted_since'] = "2000-01-01T00:00:01.000Z"

        response_view = 'deleted'
        response_doc_fcn = document_fcns[response_view]

        # Most of these are reference only, except for the fcn value
        response_params = {
            'fcn': response_doc_fcn,
            'view': response_view,
            'limit': limit,
            'page_id': 0
        }

        verbose = _process_verbose(self.parent, d, response_params)
        if verbose:
            if limit == 0:
                print(
                    "Requesting all documents from Mendeley with params: %s" % (
                        d))
            else:
                print(
                    "Requesting up to %d documents from Mendeley with params: %s" % (
                    limit, d))

        result = self.parent.make_get_request(url, models.DocumentSet.create,
                                              d, response_params)

        if limit == 0:
            # TODO: Test this when the return type is not an object ...
            result.get_all_docs()

        return result

    def create(self, doc_data, **kwargs):
        """
        https://api.mendeley.com/apidocs#!/documents/createDocument

        Parameters
        ----------
        doc_data : dict
            'title' and 'type' fields are required. Example types include:
            'journal' and 'book'. All types can be found at:
                api.definitions.document_types()
            
        TODO: Let's create a better interface for creating these values        
        
        Example
        -------
        m = API()
        data = {"title": "Motor Planning", "type": "journal", "identifiers": {"doi": "10.1177/1073858414541484"}}
        new_doc = m.documents.create(data)
        """

        

        url = BASE_URL + '/documents'

        headers = dict()
        headers['Content-Type'] = 'application/vnd.mendeley-document.1+json'

        verbose = _process_verbose(self.parent,kwargs,None)
        
        if verbose:
            pass


        return self.parent.make_post_request(url, models.Document, doc_data, headers=headers)


    def create_from_file(self, file_path):
        """

    

        https://api.mendeley.com/apidocs#!/document-from-file/createDocumentFromFileUpload
        
        TODO: We might want some control over the naming
        TODO: Support retrieval from another website
        
        """
        filename = basename(file_path)
        headers = {
            'content-disposition': 'attachment; filename=%s' % filename,
            'content-type': mimetypes.guess_type(filename)[0]}

        # TODO: This needs futher work
        pass

    def delete(self):
        """
        https://api.mendeley.com/apidocs#!/documents/deleteDocument
        """
        pass

    def update(self, doc_id, new_data):
        """
        https://api.mendeley.com/apidocs#!/documents/updateDocument
        """
        url = BASE_URL + '/documents/' + doc_id

        headers = dict()
        headers['Content-Type'] = 'application/vnd.mendeley-document.1+json'

        return self.parent.make_patch_request(url, models.Document,
                                              new_data, headers=headers)

    def move_to_trash(self, doc_id):

        url = BASE_URL + '/documents/' + doc_id + '/trash'

        headers = dict()
        headers['Content-Type'] = 'application/vnd.mendeley-document.1+json'

        resp =  self.parent.s.post(url, headers=headers, auth = self.parent.access_token)
        return

class Files(object):
    
    def __init__(self, parent):
        self.parent = parent
        self.url = BASE_URL + '/files'

    def get_single(self, **kwargs):
        """
        # https://api.mendeley.com/apidocs#!/annotations/getFiles

        THIS DOESN'T REALLY DO ANYTHING RIGHT NOW.

        Parameters
        ----------
        id :
        document_id :
        catalog_id :
        filehash :
        mime_type :
        file_name :
        size :

        Returns
        -------

        """

        doc_id = kwargs.get('document_id')

        # Not sure what this should be doing
        response_params = {'document_id': doc_id}

        # Didn't want to deal with make_get_request
        response = self.parent.s.get(url, params=kwargs, auth=self.parent.access_token)
        json = response.json()[0]

        file_id = json['id']

        file_url = self.url + '?id=' + file_id

        file_response = self.parent.s.get(file_url, auth=self.parent.access_token)

        return file_id

    def get_file_content_from_doc_id(self, doc_id, no_content=False):
        # First need to make a request to find files based on the document ID.
        # This returns the file ID for the attached file (if found)
        params = {'document_id': doc_id}
        headers = {'Content-Type': 'application/vnd.mendeley-file.1+json'}

        resp = requests.get(self.url, params=params, headers=headers, auth=self.parent.access_token)

        file_json = None
        if resp.status_code == 404:
            raise FileNotFoundError('Document could not be found.')
        elif resp.status_code != 200:
            print(resp)
            raise PermissionError('Could not connect to the server.')
        else:
            file_json = resp.json()

        if isinstance(file_json, list):
            file_json = file_json[0]

        file_name = file_json.get('file_name')
        file_id = file_json.get('id')

        if not no_content:
            # Next need to make another API request using the file ID in order
            # to retrieve the file content and download it.
            new_url = self.url + '/' + file_id
            new_params = {'file_id': file_id}
            resp = requests.get(new_url, params=new_params, auth=self.parent.access_token)

            file_content = resp.content
        else:
            file_content = None

        return file_content, file_name, file_id


    def link_file(self, file, params, file_url=None):
        """

        Parameters
        ----------
        file : dict
            Of form {'file' : Buffered Reader for file}
            The buffered reader was made by opening the pdf using open().
        params : dict
            Includes the following:
            'title' = paper title
            'id' = ID of the document to which
            the file will be attached
            (optional) '_return_type': return type of API.make_post_request
            (json, object, raw, or response)

        Returns
        -------
        Object specified by params['_return_type'].
            Generally models.LinkedFile object

        """
        # Extract info from params
        title = params.get('title')
        doc_id = params['id']
        object_fh = models.File

        # Get rid of spaces in filename
        if title is not None:
            filename = urllib_quote(title) + '.pdf'
            filename = filename.replace('/', '%2F')
        else:
            filename = doc_id + '.pdf'

        # Turn file into a dict if it is not already
        if not isinstance(file, dict):
            file = {'file': file}

        headers = dict()
        headers['Content-Type'] = 'application/pdf'
        headers['Content-Disposition'] = 'attachment; filename=%s' % filename
        headers['Link'] = '<' + BASE_URL + '/documents/' + doc_id + '>; rel="document"'

        API.make_post_request(API(), self.url, object_fh, params, headers=headers, files=file)

    def link_file_from_url(self, file, params, file_url):
        """

        Parameters
        ----------
        file : dict
            Of form {'file' : Buffered Reader for file}
            The buffered reader was made by opening the pdf using open().
        params : dict
            Includes paper title, ID of the document to which
            the file will be attached, and return type.
        file_url : str
            Direct URL to a pdf file.

        Returns
        -------
        Object specified by params['_return_type'].
            Generally models.LinkedFile object

        """
        # Extract info from params
        title = params['title']
        doc_id = params['id']
        object_fh = models.LinkedFile

        # Get rid of spaces in filename
        filename = title.replace(' ', '_') + '.pdf'

        headers = dict()
        headers['Content-Type'] = 'application/pdf'
        headers['Content-Disposition'] = 'attachment; filename=%s' % filename
        headers['Link'] = '<' + BASE_URL + '/documents/' + doc_id + '>; rel="document"'

        API.make_post_request(API(), self.url, object_fh, params, headers=headers, files=file)

    def delete(self, file_id):
        url = self.url + '/' + file_id
        params = {'file_id': file_id}
        resp = requests.delete(url, params=params, auth=self.parent.access_token)

        if not resp.ok:
            if resp.status_code == 404:
                raise FileNotFoundError()
            else:
                raise ConnectionError('Mendeley error with status code %d' % resp.status_code)


class Folders(object):
    def __init__(self, parent):
        self.parent = parent

    def create(self, name):
        url = BASE_URL + '/folders'

        # Clean up name
        name = name.replace(' ', '_')
        name = urllib_quote(name)
        params = {'name' : name}

        headers = {'Content-Type' : 'application/vnd.mendeley-folder.1+json'}

        return self.parent.make_post_request(url, models.Folder, params, headers=headers)


class MetaData(object):
    # https://api.mendeley.com/apidocs#!/metadata/getDocumentIdByMetadata
    pass


class Profiles(object):
    
    def __init__(self,parent):
        self.parent = parent
        
        #TODO: If public, provide no "me" method
        
    def get(self, **kwargs):
        """
        https://api.mendeley.com/apidocs/docs#!/profiles/getProfiles
        https://api.mendeley.com/apidocs/docs#!/profiles/get
        
        """
        pass
    
    def me(self):
        """
        https://api.mendeley.com/apidocs/docs#!/profiles/getProfileForLoggedInUser
        """
        pass
    
    #def update_my_profile()   => Let's implement this in the profile model
    


class Trash(object):
    def __init__(self, parent):
        self.parent = parent

    def get(self,
                return_type: Optional[str]=None,
                authored: Optional[bool]=None,
                deleted_since: DST=None,
                folder_id: Optional[str]=None,
                group_id: Optional[str]=None,
                include_trashed: Optional[bool]=None,
                limit: Optional[int] =20,
                modified_since: DST=None,
                order: Optional[str]=None,
                profile_id: Optional[str]=None,
                sort: Optional[str]=None,
                starred: Optional[bool]=None,
                tag: Union[List[str], str, None] = None,
                view: Optional[str] = None):
        """       
        
        Online Documentation
        --------------------
        https://api.mendeley.com/apidocs/docs#!/trash/getDeletedDocuments        
        https://api.mendeley.com/apidocs/docs#!/trash/getDocument        
        
        Parameters
        ----------
        id : 
        group_id : string
            The id of the group that the document belongs to. If not supplied 
            returns users documents.
        modified_since : string
            Returns only documents modified since this timestamp. Should be 
            supplied in ISO 8601 format.
        limit : string or int (default 20)
            Largest allowable value is 500. This is really the page limit since
            the iterator will allow exceeding this value.
        order :
            - 'asc' - sort the field in ascending order
            ' 'desc' - sort the field in descending order            
        view : 
            - 'bib'
            - 'client'
            - 'tags' : returns user's tags
            - 'patent'
            - 'all'
        sort : string
            Field to sort on. Avaiable options:
            - 'created'
            - 'last_modified'
            - 'title'
        """

        url = BASE_URL + '/trash'

        #----------------------------------------------
        #----------------------------------------------
        #JAH: At this point ...
        #----------------------------------------------
        #----------------------------------------------

        #Accept : header
        #x folder_id
        #x group_id
        #x limit
        #x modified_since

        d = dict()
        if return_type and return_type is not None:
            d['return_type'] = return_type
        if authored and authored is not None:
            d['authored'] = authored
        if deleted_since and deleted_since is not None:
            d['deleted_since'] = deleted_since
            convert_datetime_to_string(d, 'deleted_since')
        if folder_id and folder_id is not None:
            d['folder_id'] = folder_id
        if group_id and group_id is not None:
            d['group_id'] = group_id
        if include_trashed and include_trashed is not None:
            d['include_trashed'] = include_trashed
        if limit and limit is not None:
            if limit == 0:
                # 0 is code for get all
                # we'll max out our per request size
                # then merge below
                limit = 500
            d['limit'] = limit




        if 'id' in kwargs:
            id = kwargs.pop('id')
            url += '/%s/' % id
            
            
        #JAH TODO: This is duplicated with Documents.get
        #Ideally we would call out to a similar function
        view = kwargs.get('view')
        rp_view = view
        rp_doc_fcn = document_fcns[view]
            
        if view == "ids":
            #Default view of None seems to be the shortest
            #All we want is the ids, so send as little as possible
            del kwargs["view"]
        elif 'deleted_since' in kwargs:
            #Modify returned object
            rp_view = 'deleted'
    


        limit = kwargs.get('limit', 20)
        if limit == 0:
            kwargs['limit'] = 500            
            
        #Most of these are reference only, except for fcn
        response_params = {
        'fcn': rp_doc_fcn, 
        'view': rp_view, 
        'limit': limit, 
        'page_id':0}   

        verbose = _process_verbose(self.parent,kwargs,response_params)

        if verbose:
            if limit == 0:
                print("Requesting all trash documents from Mendeley with params: %s" % (kwargs))    
            else:
                print("Requesting up to %d trash documents from Mendeley with params: %s" % (limit, kwargs))
  
        result = self.parent.make_get_request(url, models.DocumentSet.create, kwargs, response_params)           
           
        if limit == 0:
            result.get_all_docs()       
        
        return result    

    def delete(self, **kwargs):
        pass
    
    def restore(self, **kwargs):
        pass


def convert_datetime_to_string(d, key):
    if key in d and isinstance(d[key], datetime):
        d[key] = d[key].strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
def _process_verbose(api,kwargs,response_params):
    
    """
    
    Parameters
    ----------
    api : API
        Contains .verbose attribute
    kwargs : dict
        Options from the user
    response_params : dict or None
        Values for the response model. 
        
    
    1) Allow user to make each call verbose or not.
    2) Have default from main API that gets called if user input is not present.
    3) Update response_params to include verbose value (for models) 
    
    """
    
    if 'verbose' in kwargs:
        verbose = kwargs.pop('verbose')
    else:
        verbose = api.verbose   
    
    if response_params is not None:
        response_params['verbose'] = verbose
    
    return verbose
