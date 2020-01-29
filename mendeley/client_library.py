# -*- coding: utf-8 -*-
"""
The goal of this code is to support hosting a client library. This module
should in the end function similarly to the Mendeley Desktop.



Jim's next goals
----------------
1) Handle deleted IDs - needs an API update
2) Meta Data Editor
    - nice query interface
    - needs to handle local/dirty docs
    - autodownload files when opening ...
3) Update by PMID ...




Features
--------
1) Initializes a representation of the documents stored in a user's library
2) Synchronizes the local library with updates that have been made remotely
    
Usage
-----
from mendeley import client_library
cl = client_library.UserLibrary(verbose=True)
wtf = cl.has_docs([14581232,10529706,12345])


"""

#Standard Library Imports
import pickle
from datetime import datetime
from timeit import default_timer as ctime
import os
import sys
import json

#Third Party Imports
import pandas as pd
from sqlalchemy import desc


# Local imports
from .api import API
from .db_tables import DB

from . import errors
from . import models
from . import utils
from . import config


# Optional Local Imports
#-----------------------------
from .optional import rr
from .optional import pdf_retrieval
#from . import db_interface
# from . import archive_library

fstr = utils.float_or_none_to_string
cld = utils.get_list_class_display


class UserLibrary:
    """
    Attributes
    ----------
    db_session :  db_interface.DBSessionInterface or None
        NOT YET IMPLEMENTED ...
    dirty_db : 
        If True specifies that the DB needs to be updated/fixed based on the 
        local docs.
    docs : Pandas DataFrame
        Library data as organized into a DataFrame.
    user_name : string
        Name of the user to process. FORMAT????
    verbose : bool
        Whether or not to print out verbose messages.
    sync_result : Sync or None
        This is used for mainly for debugging.
    
    """

    api : 'API'
    db : 'DB'
    user_name : 'str'
    verbose : 'bool'
    cleaner : 'LibraryCleaner'



    def __init__(self, user_name=None, verbose=False, sync=True, force_new=False):
        """
        Inputs
        ------
        user_name : string (default None)
            If no user is specified the default user is loaded from the 
            configuration file.
        verbose : bool (default False)
        sync : bool (default True)
        force_new : bool (default False)
            If true the library is not loaded from disk.
        """
        
        self.dirty_db = False
        self.api = API(user_name=user_name,verbose=verbose)
        self.user_name = self.api.user_name
        self.verbose = verbose


        # path handling
        # -------------
        root_path = config.get_save_root(['client_library'], True)
        save_name = utils.user_name_to_file_name(self.user_name) + '.pickle'
        self.file_path = os.path.join(root_path, save_name)

        self.db = DB(self.user_name)

        self.cleaner = LibraryCleaner(self.db)

        #TODO:
        #self._load(force_new)

        if sync:
            #self, api:API, db:DB, verbose=False
            self.sync_result = Sync(self.api,self.db,self.verbose)
        else:
            self.sync_result = None

    def __repr__(self):

        pv = ['api',        cld(self.api),
              'db',         cld(self.db),
              'dirty_db',   self.dirty_db,
              'user_name',  self.user_name,
              'file_path',  self.file_path,
              'sync_result',cld(self.sync_result),
              'verbose',    self.verbose]
        
        return utils.property_values_to_string(pv)

    def has_docs(self,ids,type='pmid'):
        """


        :param ids:
        :param type:
        :return:
        """

        output = []
        session = self.db.get_session()
        if type == 'pmid':
            for id in ids:
                temp = session.query(self.db.Document.pmid).filter_by(pmid = id).first()
                output.append(bool(temp))
            pass
        elif type =='doi':
            pass
        elif type == 'arxiv':
            pass
        else:
            raise Exception('Unrecognized id type')

        return output

    def sync(self,verbose=None):
        """
        Syncs the library with the Mendeley server.        
        
        Parameters
        ----------
        verbose : bool (default, inherit from class value, self.verbose)
        
        TODO:
        ? How do we know if something has been restored from the trash?
        """

        """
        Due to the complexity of syncing, the syncing code has been moved to
        its own class.
        """
        
        if verbose is None:
            verbose = self.verbose

        sync_result = Sync(self.api, self.db, verbose=verbose)
        self.sync_result = sync_result

    # def archive(self):
    #     archivist = archive_library.Archivist(library=self, api=self.api)
    #     archivist.archive()

    def get_document(self, 
                     doi=None, 
                     pmid=None,
                     return_json=False, 
                     allow_multiple=False, 
                     _check=False):
        """
        Returns the document (i.e. metadata) based on a specified identifier.
        
        Parameters
        ----------
        doi : string (default None)
            If specified we'll find the document based on the specified doi
        pmid : string (default None)
            If specified we'll find the document based on the specifid pmid
        index : int (default None)
        
        #TODO: Support indices ...
            
        return_json : bool (default False)
            If true, the results are returned as JSON
        allow_multiple : bool (default False)
            If true then multiple entries are allowed. This changes the return
            type from a single element to a list.
        _check : bool (default False)
            If true, then the goal is simply to assess the count of the matches
            not the value of the matches.

        Returns
        -------   
        int
            If _check is True
        models.Document object
            If return_json is False
        JSON
            If return_json is True
            
        If allow_multiple is True, then a list of results will be returned,
        regardless of wehther or not we have more than one entry.
        """

        import pdb
        pdb.set_trace()


        
        # TODO: Change this so that it interacts with the database, 
        #not the Pandas dataframe

        parse_df_rows = True
        document_json = None

        #1) Index recognition
        #-----------------------------------------------------------
        #TODO: We could support an indices input, that would return a list
        #=> "indices"
        if index is not None:
            if index < 0 or index >= len(self.docs):
                if _check and index > 0:
                    return 0
                else:
                    raise errors.UserLibraryError('Out of bounds index request')
            elif _check:
                return 1
                
            #For an index, we expect a single result
            document_json = [self.docs.ix[index]['json']]
            parse_df_rows = False

        elif doi is not None:
            #All dois in the library are stored as lower
            df_rows = self.docs[self.docs['doi'] == doi.lower()]
        elif pmid is not None:
            df_rows = self.docs[self.docs['pmid'] == pmid]
        else:
            raise errors.UserCodeError('get_document: Unrecognized identifier search option')


        # Handling of the parsing of the rows
        # ------------------------------------
        #
        #   We parse rows when 
        if parse_df_rows:
            # We parse rows when the rows to grab has not been specified
            # explicitly (i.e. as an index) and we need to determine 
            # if we found any matches
            
            rows_json = df_rows['json']
            n_results = len(rows_json)
            if n_results == 1:
                document_json = [rows_json[0]]
            elif n_results == 0:
                if _check:
                    return 0
                else:
                    if doi is not None:
                        raise errors.DocNotFoundError('DOI: "%s" not found in library' % doi)
                    elif pmid is not None:
                        raise errors.DocNotFoundError('PMID: "%s" not found in library' % pmid)
                    else:
                        raise Exception('Code logic error, this should never run')
            else: 
                if allow_multiple:
                    document_json = [x for x in rows_json]
                elif _check:
                    return n_results
                else:
                    if doi is not None:
                        raise Exception(
                                '%d DOIs found for doi: "%s", use option allow_multiple=True if multiple results is ok' 
                                        % (n_results,doi))
                    elif pmid is not None:
                        raise Exception(
                                '%d PMIDs found for pmid: %s", use option allow_multiple=True if multiple results is ok' 
                                % (n_results,pmid))
                    else:
                        raise Exception('Code logic error, this should never run')
              
        # Returning the results
        # ------------------------
        if _check:
            return len(document_json)
        elif return_json:
            if allow_multiple:
                return document_json
            else:
                return document_json[0]
        else:
            docs = [models.Document(x, self.api) for x in document_json]
            if allow_multiple:
                return docs
            else:
                return docs[0]

    def check_for_document(self, doi=None, pmid=None):
        """
        Attempts to call self.get_document and checks for error.
        If no error, the DOI has been found.

        Parameters
        ----------
        doi - string (default None)
            Document's DOI 
        pmid - string (default None)

        Returns
        -------
        bool - True if DOI is found in the Mendeley library. False otherwise.
            This function is also true if multiple matches are found
        """
        
        return self.get_document(doi=doi,pmid=pmid,
                                 _check=True,allow_multiple=True) > 0

    def add_to_library(self, 
                       doi=None, 
                       pmid=None, 
                       check_in_lib=False, 
                       add_pdf=True, 
                       file_path=None):
        """
        
        JAH: I think this method is still under development ...
        
        Parameters
        ----------
        doi : string
        check_in_lib : bool
            If true, 
        add_pdf : bool
        
        
        Improvements
        ------------
        * 
        - allow adding via PMID
        - pdf entry should be optional with default true
        - also need to handle adding pdf if possible but no error
        if not possible
        
        """
        
        #JAH: Why doesn't this take in any inputs on the check???
        if check_in_lib and self.check_for_document():
            raise errors.DuplicateDocumentError('Document already exists in library.')

        #----------------------------------------------------------------------
        # Get paper information from DOI
        """
        Even then, this requires a bit of thinking. Why are we asking rr for
        paper information? Perhaps we need another repository ...
             - Pubmed
             - Crossref
             - others????

        """

        paper_info = rr.retrieve_all_info(input=doi, input_type='doi')

        # Turn the BaseEntry object into a formatted dict for submission
        # to the Mendeley API
        formatted_entry = self._format_doc_entry(paper_info.entry)

        # Create the new document
        new_document = self.api.documents.create(formatted_entry)

        """
        add_pdf
        
        * I want to be able to specify the path to the file to add.
        * Perhaps instead we want:
            pdf = file_path
            pdf = 'must_retrieve'
            pdf = 'retrieve_or_request' - If not available, make a request for it
            pdf = 'retrive_if_possible'
            
        I'm not thrilled with this specific interface, but I'd like something
        like this.
        
        We might want an additional package that focuses on retrieving pdfs.
        The big question is how to support letting these interfaces interact
        efficiently without doing things multiple times. We can answer this 
        at a later time.
        
        pdf retrieval:
            - Interlibrary loan
            - ScholarSolutions
            - PyPub
        """

        # Get pdf
        if add_pdf:
            pdf_content = pdf_retrieval.get_pdf(paper_info)
            new_document.add_file({'file' : pdf_content})

    def update_file_from_local(self, doi=None, pmid=None):
        """
        This is for updating a file in Mendeley without losing the annotations.
        The file must be saved somewhere locally, and the file path is selected
        by using a pop up file selection window.

        Parameters
        ----------
        doi - DOI of document in library to update
        pmid - PMID of document in library to update

        """
        if doi is None and pmid is None:
            raise KeyError('Please enter a DOI or PMID for the updating document.')

        document = self.get_document(doi=doi, pmid=pmid, return_json=True)
        if document is None:
            raise errors.DOINotFoundError('Could not locate DOI in library.')

        new_file_path = self._file_selector()
        if new_file_path is None:
            return

        with open(new_file_path, 'rb') as file:
            file_content = file.read()

        doc_id = document.get('id')
        saved_annotations_string = self.api.annotations.get(document_id=doc_id)
        saved_annotations = json.loads(saved_annotations_string)
        if isinstance(saved_annotations, list):
            saved_annotations = saved_annotations[0]

        has_file = document.get('file_attached')
        if has_file:
            _, _, file_id = self.api.files.get_file_content_from_doc_id(doc_id=doc_id, no_content=True)
            self.api.files.delete(file_id=file_id)

        params = {'title': document.get('title'), 'id': doc_id}
        self.api.files.link_file(file=file_content, params=params)

        # Reconfirm that the file was added
        updated = self.get_document(doi=doi, pmid=pmid, return_json=True)
        has_file = updated.get('file_attached')
        if not has_file:
            raise FileNotFoundError('File was not attached.')

        new_annotations_string = self.api.annotations.get(document_id=doc_id)
        if new_annotations_string is None or saved_annotations_string != new_annotations_string:
            self.api.annotations.create(annotation_body=saved_annotations)


    def _file_selector(self):
        #TODO: Test this with non * imports
        #
        #Why is this line needed???
        app = QApplication(sys.argv)
        dialog = QFileDialog()
        # dialog.setFileMode(QFileDialog.DirectoryOnly)
        dialog.setViewMode(QFileDialog.List)
        dialog.setDirectory(os.path.expanduser('~'))
        if dialog.exec_():
            filenames = dialog.selectedFiles()
            return filenames[0]
        else:
            return None

    def _format_doc_entry(self, entry):
        """
        Mendeley API has specific input formatting when creating a document.
         - Parses author names and separates into separate "first_name" and
            "last_name" fields.
         - Restricts keywords from being > 50 characters. If one is found,
            it is split by spaces and saved as separate keywords.
         - Changes "publication" to "publisher" to fit syntax.
         - Sets "type" to "journal"
         - Saves DOI within "identifiers" field.

        Parameters
        ----------
        entry : BaseEntry object
            See pypub.scrapers.base_objects.py
            Unformatted paper information, usually from PaperInfo class

        Returns
        -------
        entry : dict
            Paper information with proper formatting applied.
        """

        if not isinstance(entry, dict):
            entry = entry.__dict__

        # Format author names
        authors = entry.get('authors')
        formatted_author_names = None
        if authors is not None:
            if isinstance(authors[0], str):
                author_names = [x for x in authors]
            elif isinstance(authors[0], dict):
                author_names = [x.get('name') for x in authors]
            else:
                author_names = [x.name for x in authors]
            formatted_author_names = []

            # Parse author names
            for name in author_names:
                name_dict = dict()
                name = name.strip()
                parts = name.split(' ')

                # If format is "firstname middleinitial. lastname"
                if '.' in name and len(parts) == 3:
                    name_dict['first_name'] = parts[0]
                    name_dict['last_name'] = parts[2]
                # If format is "lastname, firstname"
                elif ',' in name:
                    name_dict['first_name'] = parts[1]
                    name_dict['last_name'] = parts[0]
                # If format is "lastname firstinitial"
                elif len(parts) == 2 and '.' in parts[1]:
                    name_dict['first_name'] = parts[1]
                    name_dict['last_name'] = parts[0]
                # If format is only "lastname"
                elif len(parts) == 1:
                    name_dict['last_name'] = parts[0]
                    name_dict['first_name'] = ''
                # If there are multiple initials
                elif len(parts) > 3:
                    initials = ''
                    for part in parts:
                        if '.' in part:
                            initials += part
                        else:
                            name_dict['last_name'] = part
                    name_dict['first_name'] = initials
                # Otherwise assume format is "firstname lastname" or "firstinitial. lastname"
                else:
                    name_dict['first_name'] = parts[0]
                    name_dict['last_name'] = parts[1]
                formatted_author_names.append(name_dict)

        # Make sure keywords are <= 50 characters
        kw = entry.get('keywords')
        if kw is not None:
            # Check if it's one long string, and split if so
            if isinstance(kw, str):
                kw = kw.split(', ')
            to_remove = []
            for keyword in kw:
                if len(keyword) > 50:
                    to_remove.append(keyword)
                    smaller_keywords = keyword.split(' ')
                    for word in smaller_keywords:
                        kw.append(word)
            for long_word in to_remove:
                kw.remove(long_word)
        entry['keywords'] = kw


        # Get rid of alpha characters in Volume field
        vol = entry.get('volume')
        if vol is not None:
            entry['volume'] = ''.join(c for c in vol if not c.isalpha())

        # Get rid of alpha characters in Year field
        year = entry.get('year')
        if year is not None:
            entry['year'] = ''.join(c for c in year if not c.isalpha())
            if entry['year'] == '':
                entry['year'] = None

        doi = entry.get('doi')
        if doi is not None:
            doi = doi.lower()
            entry['identifiers'] = {'doi' : doi}

        entry['authors'] = formatted_author_names
        entry['publisher'] = entry['publication']
        entry['type'] = 'journal'

        return entry

class Sync(object):
    """
    This object should perform the syncing and include some 
    debugging information as well.
    
    Attributes
    ----------
    raw : json
    df : 

    """

    def __init__(self, api:API, db:DB, verbose=False):
        """
        
        Inputs
        ------
        api :
        raw_json : 
            
        """
        
        self.db = db
        self.api = api
        self.verbose = verbose

        self.verbose_print("Starting sync")

        #What happens to trashed documents?
        #- we can request trahsed documents ...

        #There is no notification that a document has been trashed ...
        #- we need to request trashed documents ...

        #deleted_since


        session = db.get_session()
        last_modified =  session.query(db.Document.last_modified).order_by(desc('last_modified')).first()

        dirty_docs = session.query(db.Document).filter_by(is_dirty=True).all()
        if dirty_docs:
            pass
            #I think we'll want to resolve these first, then

        new_docs = api.documents.get(modified_since=last_modified,limit=100,return_type='json')
        count = 0

        self.ids_new = []
        self.ids_modified = []
        temp = db.add_documents(new_docs)
        self.ids_new.extend(temp['new'])
        self.ids_modified.extend(temp['modified'])

        while api.has_next_link:
            count += 100
            print("Adding more docs starting at %d" % count)
            docs_to_add = api.next()
            temp = db.add_documents(docs_to_add)
            self.ids_new.extend(temp['new'])
            self.ids_modified.extend(temp['modified'])


        self.verbose_print("Sync completed")
        #trashed_docs = api.trash.get()


    def __repr__(self):
        new_str = 'list length: %d' % len(self.ids_new)
        modified_str = 'list length: %d' % len(self.ids_modified)
        pv = ['api', cld(self.api),
              'db', cld(self.db),
              'ids_new',new_str,
              'ids_modified',modified_str,
              'verbose',self.verbose]

        return utils.property_values_to_string(pv)

    def full_sync(self):

        t1 = ctime()
        self.verbose_print('Starting retrieval of all documents')

        json_data = self.api.documents.get(view='all',limit=0,return_type='json')

        self.raw_json = json_data
        self.dataframe = _raw_to_data_frame(json_data)

        #TODO: How are we referring to the database? 
        if self.db_session is not None:
            for entry in self.raw_json:
                self.db_session.add_to_db(entry)

        self.full_retrieval_time = ctime() - t1

        if self.raw_json is not None:
            self.verbose_print('Finished retrieving all documents (n=%d) in %s seconds'
                                % (len(self.raw_json), fstr(self.full_retrieval_time)))
        else:
            self.verbose_print('No documents found in %s seconds'
                               % fstr(self.full_retrieval_time))

    def update_sync(self):
        
        """
        Update Steps
        ------------
        1. 
        """
        
        self.verbose_print('Running "UPDATE SYNC"')

        start_sync_time = ctime()

        # Let's work with everything as a dataframe
        self.docs = _raw_to_data_frame(self.raw_json)

        # Determine the document that was updated most recently. We'll ask for
        # everything that changed after that time. This avoids time sync
        # issues with the server and the local computer since everything
        # is done relative to the timestamps from the server.
        newest_modified_time = self.docs['last_modified'].max()
        self.newest_modified_time = newest_modified_time

        # The problem with the above approach is that Mendeley returns
        # documents updated since AND at 'newest_modified_time'. This
        # means that the call always returns >= 1 document.
        # Try adding a second to 'newest_modified_time'
        later_modified_time = newest_modified_time + pd.Timedelta('00:00:01')

        # Remove old ids
        #------------------------------------
        self.get_trash_ids()
        #self.get_deleted_ids(newest_modified_time)
        self.get_deleted_ids(later_modified_time)
        self.remove_old_ids()

        # Process new and updated documents
        # ------------------------------------
        updates_and_new_entries_start_time = ctime()
        self.verbose_print('Checking for modified or new documents')
        #self.get_updates_and_new_entries(newest_modified_time)
        self.get_updates_and_new_entries(later_modified_time)
        self.time_modified_processing = ctime() - updates_and_new_entries_start_time
        self.verbose_print('Done updating modified and new documents')

        self.raw_json = self.docs['json'].tolist()

        self.time_update_sync = ctime() - start_sync_time

        self.verbose_print('Done running "UPDATE SYNC" in %s seconds' % fstr(self.time_update_sync))

    def get_updates_and_new_entries(self, newest_modified_time):
        """        
        # 3) check modified since - add/update as necessary
        #-------------------------------------------------
        # I think for now to keep things simple we'll relate everything
        # to the newest last modified value, rather than worrying about
        # mismatches in time between the client and the server
        """

        start_modified_time = ctime()
        
        doc_set = self.api.documents.get(modified_since=newest_modified_time, view='all',limit=0)
        nu_docs_as_json = [x.json for x in doc_set.docs]
		        
        self.new_and_updated_docs = doc_set.docs
        self.time_modified_check = ctime() - start_modified_time

        if len(nu_docs_as_json) == 0:
            return
	
        self.verbose_print('Request returned %d updated or new docs' % len(nu_docs_as_json))
	
        df = _raw_to_data_frame(nu_docs_as_json)

        is_new_mask = df['created'] > newest_modified_time
        new_rows_df = df[is_new_mask]
        updated_rows_df = df[~is_new_mask]

        # Log the new entries in the database
        
        
        #Old code
        #        #for x in range(len(new_rows_df)):
        #    row = new_rows_df.iloc[x]
        #    db_interface.add_to_db(row)
            
            
        if len(new_rows_df) > 0:
            self.verbose_print('%d new documents found' % len(new_rows_df))
            self.docs = self.docs.append(new_rows_df)
            
            self.verbose_print('Updating database with new entries')
            # Log the new entries in the database
            for x in range(len(new_rows_df)):
                row = new_rows_df.iloc[x]
                db_interface.add_to_db(row)


        #JAH TODO: I would prefer to have the message of # updated
        #first then messages about the dbupdates
        #
        #   At a quick glance I need to look more closely at the indices work    

        # Log the updated entries in the database
        for x in range(len(updated_rows_df)):
            row = updated_rows_df.iloc[x]
            db_interface.update_db_entry(row)

        
        if len(updated_rows_df) > 0:
            self.verbose_print('%d updated documents found' % len(updated_rows_df))
            in_old_mask = updated_rows_df.index.isin(self.docs.index)
            if not in_old_mask.all():
                print('Logic error, updated entries are not in the original')
                raise Exception('Logic error, updated entries are not in the original')

            updated_indices = updated_rows_df.index
            self.docs.drop(updated_indices, inplace=True)

            self.docs = pd.concat([self.docs, updated_rows_df])

    def get_trash_ids(self):
        """
        Here we are looking for documents that have been moved to the trash.
        
        ??? Can we check the trash that's been moved back to the main
        ??? => would this show up as an update?
        """

        trash_start_time = ctime()
        self.verbose_print('Checking trash')

        trash_set = self.api.trash.get(limit=0, view='ids')
        self.trash_ids = trash_set.docs

        self.verbose_print('Finished checking trash, %d documents found' % len(self.trash_ids))
        self.time_trash_retrieval = ctime() - trash_start_time

    def get_deleted_ids(self, newest_modified_time):
        """
        """
        # 2) Check deleted
        deletion_start_time = ctime()
        self.verbose_print('Requesting deleted file IDs')

        #TODO: What happens if newest_modified_time is empty????
        #   => Do we even run this code???
        temp = self.api.documents.get(deleted_since=newest_modified_time,limit=0)
        self.deleted_ids = temp.docs

        self.verbose_print('Done requesting deleted file IDs, %d found' % len(self.deleted_ids))
        self.time_deleted_check = ctime() - deletion_start_time

    def remove_old_ids(self):
        """
        JAH: When is this called????
        """
        # Removal of ids
        # --------------
        ids_to_remove = self.trash_ids + self.deleted_ids
        if len(ids_to_remove) > 0:
            delete_mask = self.docs.index.isin(ids_to_remove)
            keep_mask = ~delete_mask
            self.n_docs_removed = sum(delete_mask)
            self.docs = self.docs[keep_mask]

    def verbose_print(self, msg):
        if self.verbose:
            print(msg)

class LibraryCleaner():

    db : 'DB'

    def __init__(self,db : DB):
        self.db = db

    def get_docs_no_pmid(self,since=None,sort=None,limit=None):
        """

        sort:
            'old_first'
            'new_first'

        :param since:
        :param sort:
        :param limit:
        :return:
        """

        #TODO: implement since ...

        session = self.db.get_session()

        Doc = self.db.Document

        q = session.query(Doc).filter_by(pmid=None)
        if sort is 'new_first' or sort is None:
            q.order_by(Doc.last_modified)
        else:
            q.order_by(desc(Doc.last_modified))


        if limit is not None:
            q.limit(limit)

        #desc
        wtf = q.all()

        import pdb
        pdb.set_trace()
        pass


def parse_datetime(x):
    return datetime.strptime(x, "%Y-%m-%dT%H:%M:%S.%fZ")


# def datetime_to_string(x):
#    return x.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

def parse_issn(x):
    # This value is not necessarily clean
    # e.g 17517214 => 1751-7214???
    try:
        return x.get('issn', '')
    except:
        return ''


def parse_pmid(x):
    try:
        return x.get('pmid', '')
    except:
        return ''


def parse_doi(x):
    try:
        return x.get('doi', '').lower()
    except:
        return ''

def raise_(ex):
    raise ex