# -*- coding: utf-8 -*-
"""
This module is meant to implement all functions described at:

1) https://dev.mendeley.com/methods/
    - This site shows request parameters a bit more 
    
2) https://api.mendeley.com/apidocs/
    - Testing interface, nicer organization
    

General Usage
-------------
from mendeley import API
user_api = API()
public_api = API('public')


Request Options
---------------
In addition to the options of a given function, the following options are also
supported:

    TODO: fill this in: example _return_type

Method Types (from Mendeley, apidocs)
-------------------------------------
Annotations
    GET     /annotations (document_id)     - Annotations.get
    POST    /annotations (document_id)
    DELETE  /annotations/{annotation_id}
    GET     /annotations/{annotation_id}
    PATCH   /annotations/{annotation_id}
    
Catalog
    GET /catalog
    GET /catalog/{catalogId}

Document_Types
    GET /document_types - Definitions.document_types

Document From File    
    POST /documents

Documents
    GET     /documents
    POST    /documents
    DELETE  /documents/{id}
    GET     /documents/{id}
    PATCH   /documents/{id}
    POST    /documents/{id}/trash
    GET     /documents/v1/{document_id}/files
    POST    /documents/v1/{document_id}/files
    DELETE  /documents/v1/{document_id}/files/{file_id}
    GET     /documents/v1/{document_id}/files/{file_id}

File Contents
    POST /file_contents
    POST /file_contents
    
Files
    GET     /files   - Files.get
    POST    /files
    DELETE  /files/{file_id}
    GET     /files/{file_id} - Files.get_file_bytes

Folders
    GET     /folders
    POST    /folders
    DELETE  /folders/{id}
    GET     /folders/{id}
    PATCH   /folders/{id}
    GET     /folders/{id}/documents
    POST    /folders/{id}/documents
    DELETE  /folders/{id}/documents/{document_id}

Groups (Not Implemented)
    GET /groups
    GET /groups/{id}
    GET /groups/{id}/members

groups-v2 : Groups (Not Implemented)
    GET /groups/v2
    POST /groups/v2
    DELETE /groups/v2/{group_id}
    GET /groups/v2/{group_id}
    TODO

identifier_types : Document identifier types
    GET /identifier_types   Definitions.doc_id_types
    
institutions : Institutions
    GET /institutions    - Deprecated?
    GET /institutions/{id}
    
metadata : Documents Metadata Lookup
    GET /metadata
    
profiles : Profiles
    GET /profiles/v2
    GET /profiles/v2/{id}
    GET /profiles/v2/me
    PATCH /profiles/v2/me
    
documents : Library search
    GET /search/documents
    
subject_areas : Subject areas
    GET /subject_areas
    
trash : Trash
    GET /trash
    DELETE /trash/{id}
    GET /trash/{id}
    POST /trash/{id}/restore
    
user_roles : User roles
    GET /user_roles
    
    


OLD methods
----------------------------
Annotations
    GET /annotations

    

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
from typing import Optional, Union, List, Literal
import sys
import mimetypes
from os.path import basename
from datetime import datetime
import json
import urllib

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

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36"

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

class API2(object):
    
    """
    from mendeley import API, API2
    api = API()
    m = API2(api)
    
    """
    
    def __init__(self,api):
        
        #TODO: Support loading api if not passed in
        
        self.api = api
        self.retrieval = Retrieval(api)
        pass
    
    def __repr__(self):
        pv = [
            'api',cld(self.api),
            'retrieval',cld(self.retrieval),
            ]
        return utils.property_values_to_string(pv)

class Retrieval(object):
    
    def __init__(self,api):
        
        """
        from mendeley import API, API2
        api = API()
        m = API2(api)
        
        d = m.retrieval.get_document()
        
        
        """
        
        self.get_document = api.documents.get
        self.get_files = api.files.get
        
    def __repr__(self):
        pv = [
            '---','--- method props ---',
            'get_document','',
            'get_files','',
            ]
        return utils.property_values_to_string(pv)
        

class Search(object):
    
    def __init__(self,api):
        
        """
        from mendeley import API, API2
        api = API()
        m = API2(api)
        
        d = m.retrieval.get_document()
        
        
        """
        
        self.search_user_library = api.documents.search
        self.search_catalog = api.catalog.get

class Create(object):
    pass
    
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
            - <other user names> : loads other user info from user_config.py
        verbose : str
        force_reload_auth : bool (default False)
            If true, the authorization is recomputed even if it hasn't expired.
        default_return_type : {'object','json','raw','response'}
        
        Improvements
        ------------
        1. Support a user object as input
        
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
        self.catalog = Catalog(self)
        self.definitions = Definitions(self)
        self.documents = Documents(self)
        self.files = Files(self)
        self.folders = Folders(self)
        self.metadata = MetaData(self)
        self.profiles = Profiles(self)
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
            'catalog',cld(self.catalog),
            'definitions',cld(self.definitions),
            'documents',cld(self.documents),
            'files',cld(self.files),
            'folders',cld(self.folders),
            'trash',cld(self.trash),
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
                         params=None,
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
            
            
        response_params : dict
            This gets passed to the object.
            
        headers :
            
            
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
        
        
        #https://stackoverflow.com/questions/21823965/use-20-instead-of-for-space-in-python-query-parameters
        params = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

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

        return self.handle_return(resp, 
                                  return_type, 
                                  response_params, 
                                  object_fh)

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
        
        if return_type == 'object':
            if response_params is None:
                return object_fh(req.json(), self)
            else:
                return object_fh(req.json(), self, response_params)
        elif return_type == 'json':
            return req.json()
        elif return_type == 'raw':
            return req.text
        elif return_type == 'response':
            return req
        elif return_type == 'ids':
            temp = req.json()
            return [x['id'] for x in temp]
        else:
            print('-----------------------')
            print(return_type)
            print('-----------------------')
            raise Exception('No match found for return type')




class Annotations(object):
    
    def __init__(self, parent):
        self.parent = parent
        self.url = BASE_URL + '/annotations'

    def get(self,             
            return_type: Optional[str]=None,
            verbose: Optional[bool]=None,
            deleted_since: DST=None,
            document_id: Optional[str]=None,
            group_id: Optional[str]=None,
            include_trashed: Optional[bool]=None,
            limit: Optional[int]=20,
            modified_since: DST=None):
        """
        https://api.mendeley.com/apidocs#!/annotations/getAnnotations
        
        
        Example
        -------
        from mendeley import API
        m = API()
        
        #1) Generic request to get annotations
        a = m.annotations.get()
        
        #2) Requested for annotations from a specific document
        d = m.documents.search(title='Analysis of a model for excitation of myelinated nerve.')
        #TODO: We will eventually support getting annotations directly
        #from the document
        doc_id = d.docs[0].id
        a = m.annotations.get(document_id=doc_id)
        
        
        
        """

        d = dict()
        if return_type and return_type is not None:
            d['return_type'] = return_type
        if verbose and verbose is not None:
            d['verbose'] = verbose
        if deleted_since and deleted_since is not None:
            d['deleted_since'] = deleted_since
            convert_datetime_to_string(d, 'deleted_since')   
        if document_id and document_id is not None:
            d['document_id'] = group_id
        if group_id and group_id is not None:
            d['group_id'] = group_id
        if include_trashed and include_trashed is not None:
            d['include_trashed'] = include_trashed
        if limit and limit is not None:
            if limit == 0:
                #Largest allowable value
                d['limit'] = 200
            else:
                d['limit'] = limit
        if modified_since and modified_since is not None:
            d['modified_since'] = modified_since
            convert_datetime_to_string(d, 'modified_since')
        
        headers = {'Content-Type' : 'application/vnd.mendeley-annotation.1+json'}

        return self.parent.make_get_request(self.url, 
                                            models.AnnotationSet, 
                                            d, 
                                            headers=headers)

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
    
    def __repr__(self):
        pv = [
            '-------methods-------','-------------------',
            'get','get',
            'create','create',
            'delete','delete',
            ]
        return utils.property_values_to_string(pv)


class Catalog(object):
    
    def __init__(self, parent):
        self.parent = parent
        
    def get(self,             
                return_type: Optional[str]=None,
                verbose: Optional[bool]=None,
                arxiv: Optional[str]=None,
                author_profile_id: Optional[str]=None,
                cid: Optional[str]=None,
                document_id: Optional[str]=None,
                doi: Optional[str]=None,
                filehash: Optional[str]=None,
                isbn: Optional[str]=None,
                issn: Optional[str]=None,
                pii: Optional[str]=None,
                pmid: Optional[str]=None,
                pui: Optional[str]=None,
                scopus: Optional[str]=None,
                sgr: Optional[str]=None,
                url: Optional[str]=None,
                view: Optional[str]=None):

        """
                
        Parameters
        ----------
        arxiv
        author_profile_id
        cid :
            ID in the Mendeley Catalog (Catalog ID)
        document_id : string
            
        doi : string
            Digital object identifier.
        filehash : 
            MD5?
        isbn :
        issn : 
        pii : string
            Publisher identifier. See scientedirect for examples:
            e.g., https://www.sciencedirect.com/science/article/pii/B9781560534334500158
            see: https://en.wikipedia.org/wiki/Publisher_Item_Identifier
        pmid : string
            Pubmed ID
        pui : 
        scopus : string
        sgr : string
            Scopus Group Identifier
        url : string
        view : string
             - bib
             - stats
             - client - this option doesn't make much sense
             - all

        Examples
        --------
        from mendeley import API
        m = API()
        c = m.catalog.get(pmid='11826063')
        c = m.catalog.get(pmid='11826063',view='bib')
        c = m.catalog.get(cid='92d3ca3c-1e07-31c0-88e3-7bca73c26179')
        c = m.catalog.get(pui='2002602386')
        
        Improvements
        ------------
        1. Implement unwrap single
        """
        
        #unwrap_single = False
        d = dict()
        if return_type and return_type is not None:
            d['return_type'] = return_type
        if verbose and verbose is not None:
            d['verbose'] = verbose
        if arxiv and arxiv is not None:
            d['arxiv'] = arxiv 
        if author_profile_id and author_profile_id is not None:
            d['author_profile_id'] = author_profile_id
        if document_id and document_id is not None:
            d['document_id'] = document_id
        if doi and doi is not None:
            d['doi'] = doi
        if filehash and filehash is not None:
            d['filehash'] = filehash 
        if isbn and isbn is not None:
            d['isbn'] = isbn
        if issn and issn is not None:
            d['issn'] = issn
        if pii and pii is not None:
            d['pii'] = pii
        if pmid and pmid is not None:
            d['pmid'] = pmid 
        if pui and pui is not None:
            d['pui'] = pui
        if scopus and scopus is not None:
            d['scopus'] = scopus
        if sgr and sgr is not None:
            d['sgr'] = sgr        
        if url and url is not None:
            d['url'] = url
        if view and view is not None:
            d['view'] = view   
        
        headers = {'Content-Type' : 'application/vnd.mendeley-annotation.1+json'}

        url2 = BASE_URL + '/catalog'
        if cid and cid is not None:
            url2 += '/%s/' % cid

        response_params = {'fcn': catalog_fcns[view],
                           'view': view,
                           'page_id':0}
        
        verbose = _process_verbose(self.parent,d,response_params)

        return self.parent.make_get_request(url2, 
                                     models.DocumentSet.create, 
                                     d, 
                                     response_params,
                                     headers=headers)
    
        #if unwrap_single:
        #    pass
        
class Definitions(object):
    """
    TODO: These values should presumably only be queried once ...
    """

    def __init__(self, parent):
        self.parent = parent
        

        
    def doc_id_types(self):
        """
        
        https://api.mendeley.com/apidocs/docs#!/identifier_types/getAllDocumentTypes
        
        Example
        -------        
        from mendeley import API
        m = API()
        id_types = m.definitions.doc_id_types()
        """

        url = BASE_URL + '/identifier_types'
        
        return self.parent.make_get_request(url, models.identifier_types)



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

    def __repr__(self):
        pv = [
            '-------methods-------','-------------------',
            'academic_statuses','academic_statuses',
            'subject_areas','subject_areas',
            'document_types','document_types',
            ]
        return utils.property_values_to_string(pv)


class Documents(object):
    """

    GET    /documents
    POST   /documents
    DELETE /documents/{id}
    GET    /documents/{id}
    PATCH  /documents/{id}
    POST   /documents/{id}/trash
    GET    /documents/v1/{document_id}/files
    POST   /documents/v1/{document_id}/files
    DELETE /documents/v1/{document_id}/files/{file_id}
    GET    /documents/v1/{document_id}/files/{file_id}

    """
    def __init__(self, parent):
        self.parent = parent
        

    #TODO: make names mandatory for get
    def get(self,
            return_type: Optional[str]=None,
            verbose: Optional[bool]=None,
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
            
        Other Parameters
        ----------------
        return_type
            - 'object'
            - 'json'
            - 'raw'
            - 'response'
            - 'ids'
        verbose
        

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
        
        d = m.documents.get()
        
        
        m = API(default_return_type='json')
        d = m.documents.get(limit=1)
        
        """

        url = BASE_URL + '/documents'

        d = dict()
        if return_type and return_type is not None:
            d['return_type'] = return_type
        if verbose and verbose is not None:
            d['verbose'] = verbose
            
            
            
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
  
        result = self.parent.make_get_request(url, 
                                              models.DocumentSet.create, 
                                              d, 
                                              response_params)

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

        return self.parent.make_get_request(url, models.DocumentSet.create, 
                                            d, response_params)

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
    
    
    def search(self,  
            return_type: Optional[str]=None,
            verbose: Optional[bool]=None,
            abstract: Optional[str]=None,
            author: Optional[str]=None,
            identifier: Optional[bool]=None,
            limit: Optional[int]=10,
            max_year: Optional[int]=None,
            min_year: Optional[int]=None,
            query: Optional[str]=None,
            source: Optional[str]=None,
            tag: Optional[str]=None,
            title: Optional[str]=None,
            use_and: Optional[bool]=None,
            view: Optional[str] = None):
        
        """
        https://api.mendeley.com/apidocs/docs#!/documents_0/search
        
        Multiple search fields may be specified. Callers must provide either 
        a query, or at least one of title, author, source or abstract. 
        Setting a minimum or maximum year excludes documents with no defined 
        year.
        
        
        Parameters
        ----------
        abstract :
        author :
        identifier :
        limit :
        max_year :
        min_year :
        query :
        source :
        tag :
        title :
        use_and :logical
        view :
            
            
        Examples
        --------
        from mendeley import API
        m = API()
        d = m.documents.search(title='Analysis of a model for excitation of myelinated nerve.')
        
        """
        
        
        url = BASE_URL + '/search/documents'
        
        d = dict()
        if return_type and return_type is not None:
            d['return_type'] = return_type
        if verbose and verbose is not None:
            d['verbose'] = verbose
            
        if abstract and abstract is not None:
            d['abstract'] = abstract
        if author and author is not None:
            d['author'] = author
        if identifier and identifier is not None:
            d['identifier'] = identifier
        if limit and limit is not None:
            if limit == 0:
                #0 is code for get all
                #we'll max out our per request size
                #then merge below
                d['limit'] = 500
            else:
                d['limit'] = limit
        if max_year and max_year is not None:
            d['max_year'] = max_year
        if min_year and min_year is not None:
            d['min_year'] = min_year
        if query and query is not None:
            d['query'] = query
        if source and source is not None:
            d['source'] = source
        if tag and tag is not None:
            d['tag'] = tag
        if title and title is not None:
            d['title'] = title
        if use_and and use_and is not None:
            d['use_and'] = use_and
        if view and view is not None:
            d['view'] = view

        response_doc_fcn = document_fcns[view]
        response_view = view
        
        #Most of these are reference only, except for the fcn value
        response_params = {
            'fcn': response_doc_fcn,
            'view': response_view,
            'limit': limit,
            'page_id':0
            }

        verbose = _process_verbose(self.parent,d,response_params)
        if verbose:
            #TODO: Fix this, not valid for search
            if limit == 0:
                print("Requesting all documents from Mendeley with params: %s" % (d))
            else:
                print("Requesting up to %d documents from Mendeley with params: %s" % (limit, d))
  
        result = self.parent.make_get_request(url, models.DocumentSet.create, d, response_params)

        if limit == 0:
            #TODO: Test this when the return type is not an object ...
            result.get_all_docs()       
        
        return result
        
        

class Files(object):
    """
    
    
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.url = BASE_URL + '/files'
    
    def get(self,
            return_type: Optional[str]=None,
            verbose: Optional[bool]=None,
            added_since: Optional[str]=None,
            catalog_id: Optional[str]=None,
            deleted_since: Optional[str]=None,
            document_id: Optional[str]=None,
            group_id: Optional[str]=None,
            include_trashed: Optional[bool]=None,
            limit: Optional[str]=None):
        
        """
        
        Returns information about files.

        Parameters
        ----------
        return_type
        added_since
        catalog_id
        deleted_since
        document_id
        group_id
        include_trashed
        limit
        
        Example
        -------
        from mendeley import API
        m = API()
        d = m.files.get(limit=20)
        """
        
        d = dict()
        if return_type and return_type is not None:
            d['return_type'] = return_type
        if added_since and added_since is not None:
            d['added_since'] = added_since
        if catalog_id and catalog_id is not None:
            d['catalog_id'] = catalog_id
        if deleted_since and deleted_since is not None:
            d['deleted_since'] = deleted_since
        if document_id and document_id is not None:
            d['document_id'] = document_id
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
                
        response_params = {
            'fcn': models.File,
            'limit': limit,
            'page_id': 0
            }

        verbose = _process_verbose(self.parent,d,response_params)
        
        if verbose:
            print('Retrieving file info')
        
        result = self.parent.make_get_request(self.url, 
                                              models.FileSet,
                                              d, 
                                              response_params)

        return result
    
    def get_file_bytes(self,file_id):
        """
        
        from mendeley import API
        m = API()
        d = m.files.get(limit=20)
        content = m.files.get_file_content(d.docs[0].id)
        

        """
        
        # Next need to make another API request using the file ID in order
        # to retrieve the file content and download it.
        new_url = self.url + '/' + file_id
        new_params = {'file_id': file_id}
        resp = requests.get(new_url, 
                            params=new_params, 
                            auth=self.parent.access_token)

        file_content = resp.content
        
        return file_content
        
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


class Initializer(object):
    
    
    """
        type (com.mendeley.documents.api.DocumentType) = 
        ['journal' or 'book' or 'generic' or 'book_section' or 
         'conference_proceedings' or 'working_paper' or 'report' 
         or 'web_page' or 'thesis' or 'magazine_article' or 'statute' or 
         'patent' or 'newspaper_article' or 'computer_program' or 'hearing' 
         or 'television_broadcast' or 'encyclopedia_article' or 'case' or 
         'film' or 'bill'],
        
    """
    
    def __init__(self,
                 title: str,
                 dtype: Literal["test"],
                 abstract: Optional[str]=None,
                 accessed: Optional[str]=None,
                 authored: Optional[bool]=None,
                 authors: Optional[list[dict]]=None,
                 chapter: Optional[str]=None,
                 citation_key: Optional[str]=None,
                 city: Optional[str]=None,
                 code: Optional[str]=None,
                 confirmed: Optional[bool]=None,
                 country: Optional[str]=None,
                 day: Optional[int]=None,
                 department: Optional[str]=None,
                 edition: Optional[str]=None,
                 editors: Optional[list[dict]]=None,
                 folder_uuids: Optional[list[str]]=None,
                 genre: Optional[str]=None,
                 group_id: Optional[str]=None,
                 hidden: Optional[bool]=None,
                 identifiers: Optional[dict]=None,  
                 institution: Optional[str]=None,
                 issue: Optional[str]=None,
                 keywords: Optional[list[str]]=None,
                 language: Optional[str]=None,
                 medium: Optional[str]=None,
                 month: Optional[int]=None,
                 notes: Optional[str]=None,
                 pages: Optional[str]=None,
                 patent_application_number: Optional[str]=None,
                 patent_legal_status: Optional[str]=None,
                 patent_owner: Optional[str]=None,
                 private_publication: Optional[bool]=None,
                 profile_id: Optional[str]=None,
                 publisher: Optional[str]=None,
                 read: Optional[bool]=None,
                 reprint_edition: Optional[str]=None,
                 revision: Optional[str]=None,
                 series: Optional[str]=None,
                 series_editor: Optional[str]=None,
                 series_number: Optional[str]=None,
                 short_title: Optional[str]=None,
                 source: Optional[str]=None,
                 source_type: Optional[str]=None,
                 starred: Optional[bool]=None,
                 tags: Optional[list[str]]=None,
                 translators: Optional[list[dict]]=None,
                 user_context: Optional[str]=None,
                 volume: Optional[str]=None,
                 websites: Optional[list[str]]=None,
                 year: Optional[int]=None):
        
        pass
    

    
    
    
    def doc(self):
        pass
    
    
    def identifiers(self):
        pass
    
    def p(self,
          last: str,
          first: Optional[str]=None,
          scopus: Optional[str]=None):
        
        "Shorter version of person"
        
        d = dict()
        d['last'] = last
        
        if first and first is not None:
            d['first'] = first
        if scopus and scopus is not None:
            d['scopus'] = scopus
            
        return d       
        
    
    def person(self,
               last_name: str,
               first_name: Optional[str]=None,
               scopus_author_id: Optional[str]=None):
        
        d = dict()
        d['last_name'] = last_name
        
        if first_name and first_name is not None:
            d['first_name'] = first_name
        if scopus_author_id and scopus_author_id is not None:
            d['scopus_author_id'] = scopus_author_id
            
        return d
    
    

class MetaData(object):
    # https://api.mendeley.com/apidocs#!/metadata/getDocumentIdByMetadata
    
    def __init__(self,parent):
        self.parent = parent
        
    def get(self,
            return_type: Optional[str]=None,
            verbose: Optional[bool]=None,
            arxiv: Optional[str]=None,
            authors : Optional[str]=None,
            doi: Optional[str]=None,
            filehash: Optional[str]=None,
            isbn: Optional[str]=None,
            pmid : Optional[str]=None,
            source: Optional[str]=None,
            title: Optional[str]=None,
            year: Optional[str]=None):
        """
        
        

        Parameters
        ----------
        return_type : Optional[str], optional
            DESCRIPTION. The default is None.
        verbose : Optional[bool], optional
            DESCRIPTION. The default is None.
        arxiv : Optional[str], optional
            DESCRIPTION. The default is None.
        authors : Optional[str], optional
            DESCRIPTION. The default is None.
        doi : Optional[str], optional
            DESCRIPTION. The default is None.
        filehash : Optional[str], optional
            DESCRIPTION. The default is None.
        isbn : Optional[str], optional
            DESCRIPTION. The default is None.
        pmid : Optional[str], optional
            DESCRIPTION. The default is None.
        source : Optional[str], optional
            DESCRIPTION. The default is None.
        title : Optional[str], optional
            DESCRIPTION. The default is None.
        year : Optional[str], optional
            DESCRIPTION. The default is None.

        Returns
        -------
        result : TYPE
            DESCRIPTION.
            
            
        Examples
        --------
        This isn't working all that well. Not sure why
        
        #TODO: Better examples that call docs first
        
        
        filehash = '07e3d3dc3f2838dfe5d2ba553046eb9c07913a81'
        filehash = '6e01e190431fdfe9f18ed7fe3d34ebde'
        
        #Not working even though filehash is valid
        filehash = '5279de540e3d884fe8afc441a8809577326af7bd'
        
        from mendeley import API
        m = API()
        
        
        c = m.metadata.get(filehash=filehash)
        
        
        title = "Sensory and motor responses of precentral cortex cells during comparable"
        from mendeley import API
        m = API()
        c = m.metadata.get(title=title)
        
        
        
        

        """
            
        d = dict()   
        if return_type and return_type is not None:
            d['return_type'] = return_type
        if verbose and verbose is not None:
            d['verbose'] = verbose
        if arxiv and arxiv is not None:
            d['arxiv'] = arxiv
        if authors and authors is not None:
            d['authors'] = authors
        if doi and doi is not None:
            d['doi'] = doi
        if filehash and filehash is not None:
            d['filehash'] = filehash
        if isbn and isbn is not None:
            d['isbn'] = isbn
        if pmid and pmid is not None:
            d['pmid'] = pmid
        if source and source is not None:
            d['source'] = source
        if title and title is not None:
            d['title'] = title    
        if year and year is not None:
            d['year'] = year                
            
            
        headers = {'Accept':'application/vnd.mendeley-document-lookup.1+json'}    
                        
        response_params = {
                'page_id':0
                }
            
        verbose = _process_verbose(self.parent,d,response_params)
        
        url = BASE_URL + '/metadata'
        
        try:
            result = self.parent.make_get_request(url, 
                                                  models.json_only, 
                                                  d, 
                                                  response_params,
                                                  headers=headers)  
        except:
            result = None
            

        return result              
            
        
        """
        filehash OR
        title OR
            - improved by authors or source
        identifier
        
        filehash = '07e3d3dc3f2838dfe5d2ba553046eb9c07913a81'
        filehash = '6e01e190431fdfe9f18ed7fe3d34ebde'
        
        #Not working even though filehash is valid
        filehash = '5279de540e3d884fe8afc441a8809577326af7bd'
        
        title = "Sensory and motor responses of precentral cortex cells during comparable"
        
        from mendeley import API
        m = API()
        
        c = m.metadata.get(filehash=filehash)
        
        c = m.metadata.get(title=title)
        
        
        """



class Profiles(object):
    
    #GET   /profiles/v2
    #GET   /profiles/v2/{id}
    #GET   /profiles/v2/me
    #PATCH /profiles/v2/me
    
    def __init__(self,parent):
        self.parent = parent
        self.url = BASE_URL + '/profiles/v2'
        
        #TODO: If public, provide no "me" method
        
    def get(self,             
            return_type: Optional[str]=None,
            verbose: Optional[bool]=None,
            authored_document_catalog_id: Optional[str]=None,
            email: Optional[str]=None,
            scopus_author_id: Optional[str]=None):
        """
        
        Parameters
        ----------
        authored_document_catalog_id : string
        email : string
        scopus_author_id : string
        
        """
        d = dict()
        if return_type and return_type is not None:
            d['return_type'] = return_type
        if verbose and verbose is not None:
            d['verbose'] = verbose
        if authored_document_catalog_id and authored_document_catalog_id is not None:
            d['authored_document_catalog_id'] = authored_document_catalog_id
        if email and email is not None:
            d['email'] = email
        if scopus_author_id and scopus_author_id is not None:
            d['scopus_author_id'] = scopus_author_id    
            
        response_params = {
                'page_id':0
                }
            
        verbose = _process_verbose(self.parent,d,response_params)
        
        result = self.parent.make_get_request(self.url, 
                                              models.Profile, 
                                              d, 
                                              response_params)
        
        return result
            
    
    def me(self):
        """
        
        Examples
        --------
        from mendeley import API
        m = API()
        p = m.profiles.me()
        

        """
        d = dict()
        response_params = {}
        url = self.url + '/me'
        result = self.parent.make_get_request(url, 
                                              models.Profile, 
                                              d)
        
        return result
    
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
