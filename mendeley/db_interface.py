"""
Status: Jim is currently rewriting

https://stackoverflow.com/questions/40450591/converting-json-to-sql-table

DB
- create table
- add entries to table
    - 1) for now, overwrite local
    - 2) eventually, if any dirty, then fail (handle later)


"""

import math
import os

# Third party imports
import pandas as pd
from sqlalchemy.types import Integer, Text, String, DateTime


# Local imports
from . import utils
from .optional import MissingModule

#Optional Imports
#------------------------------------
#pypub.paper_info 
from mendeley.optional import PaperInfo

#TODO: This is a poor import name, fix this
#pypub.scrapers
from mendeley.optional import base_objects as obj


#TODO: Enumerate errors
from . import errors

#Public Interface
#------------------------------------------------
db_available = type(db) is not MissingModule

class DBSessionInterface(object):

    """
    Attributes
    ----------
    s : 
    
    """
    
    def __init__(self, user_name):
        
        self.user_name = user_name
        root_path = self._get_file_save_path()


        #TODO: Create the DB at this point ...


                
        if db_available:
            self.s = db.DB_Session(user_name, root_path)
        else:
            raise Exception('Library database code is not available')

    def _get_file_save_path(self):
        temp = utils.get_save_root()
        #Let's go one folder up
        save_path = os.path.split(temp)[0]
        return save_path

    def load_db_session(user_name):
        #1 Determine save path ...
        if db_available:
            #TODO: Implement this ...
            return None
        else:
            return Exception('Library database code is not available')

    def add_to_db(self,info):
        """
        Inputs
        ------
        info : dict, dataframe entry, pypub entry
        """
        paper_info = _make_paper_info(info)
        has_file = info.get('file_attached')
        db.log_info(paper_info=paper_info, has_file=has_file)


    def update_db_entry(self, info):
        new_info = _make_paper_info(info)
    
        # Get the saved information that exists for a given entry
        saved_info = db.get_saved_entry_obj(new_info)
    
        comparison_fields = saved_info.fields
        author_fields = saved_info.author_fields
        main_paper_id = saved_info.main_paper_id
    
        # Turn the new information into a combined dict
        new_full_dict = new_info.__dict__.copy()
        new_full_dict.update(new_info.entry.__dict__)
        if new_full_dict.get('authors') is not None:
            new_full_dict['authors'] = [author.__dict__ for author in new_full_dict['authors']]
    
        # Turn saved information into a combined dict
        saved_full_dict = saved_info.__dict__.copy()
        saved_full_dict.update(saved_info.entry.__dict__)
        if saved_full_dict.get('authors') is not None:
            saved_full_dict['authors'] = [author.__dict__ for author in saved_full_dict['authors']]
    
        updating_fields = []
        updating_values = []
    
        # Determine which fields have changed and need to be updated
        for field in comparison_fields:
            saved = saved_full_dict.get(field)
            new = new_full_dict.get(field)
            if saved == new:
                continue
    
            elif field == 'authors':
                # Each author is its own row in a separate Authors table.
                # This code replaces the saved bank of authors for a paper
                # with the new information. This covers creation and deletion
                # of authors, as well as updates to specific fields.
                for author in new:
                    if author not in saved:
                        db.add_author(author, main_paper_id=main_paper_id)
                for author in saved:
                    if author not in new:
                        db.delete_author(author, main_paper_id=main_paper_id)
    
            else:
                updating_fields.append(field)
                if saved is not None:
                    updating_values.append(saved)
                else:
                    updating_values.append(new)
    
        # Make the updating requests
        db.update_general_fields(new_full_dict.get('title'), updating_field=updating_fields,
                                 updating_value=updating_values, filter_by_title=True)


    def update_entry_field(self, identifying_value, updating_field, 
                           updating_value, 
                           filter_by_title=False, 
                           filter_by_doi=False):
        """
        """
        
        db.update_entry_field(identifying_value, updating_field, updating_value,
                              filter_by_title=filter_by_title, 
                              filter_by_doi=filter_by_doi)


    def add_reference(self, refs, main_doi, main_title=None):
        """
        Inputs
        ------
        """
        db.add_references(refs=refs, main_paper_doi=main_doi,
                          main_paper_title=main_title)


    def update_reference_field(self, identifying_value, 
                               updating_field, 
                               updating_value, 
                               citing_doi=None, 
                               authors=None,
                               filter_by_title=False, 
                               filter_by_doi=False, 
                               filter_by_authors=False):
        db.update_reference_field(identifying_value, updating_field, updating_value, 
                                  citing_doi=citing_doi, 
                                  authors=authors,
                               filter_by_title=filter_by_title, 
                               filter_by_doi=filter_by_doi,
                               filter_by_authors=filter_by_authors)


    def check_for_document(self,doi):
        """
        JAH: What is this used for ??????
        """
        try:
            docs = db.get_saved_info(doi)
        except errors.MultipleDoiError:
            docs = None
            pass
    
        if docs is not None:
            return True
        else:
            return False


    def follow_refs_forward(self,doi):
        
        """
        """
        return db.follow_refs_forward(doi)








def check_multiple_constraints(params):
    # Params is a dict

    # first_key, first_value = params.popitem()
    # query_results = db.main_paper_search_wrapper(first_key, first_value)
    query_results = db.get_all_main_papers()

    for key, value in params.items():
        temp = []
        for result in query_results:
            search_value = getattr(result, key, '')
            if search_value is None:
                continue
            else:
                if value.lower() in search_value.lower():
                    temp.append(result)
        query_results = temp
        # query_results = [result for result in query_results if value.lower() in str(getattr(result, key, '')).lower()]
        if len(query_results) == 0:
            return None

    return query_results


def delete_reference(ref):
    db.delete_reference(ref)


def _make_paper_info(info):
    """
    
    Inputs
    ------
    info : 
    
	"""
    if isinstance(info, PaperInfo):
        return info
    elif isinstance(info, dict):
        paper_info = _mendeley_json_to_paper_info(info)
        return paper_info
    elif isinstance(info, pandas.core.series.Series):
        paper_info = _mendeley_df_to_paper_info(info)
        return paper_info
    else:
        raise TypeError('Information could not be formatted for database entry.')


def _mendeley_df_to_paper_info(df_row):
    
    #TODO: 
    #   Pull the original json and have one point of entry for this info ...
    
    df_dict = df_row.to_dict()
    paper_info = PaperInfo()

    # Catch NaNs, which are default Pandas values
    for key in df_dict.keys():
        if isinstance(df_dict.get(key), float):
            if math.isnan(df_dict.get(key)):
                df_dict[key] = None

    entry = obj.BaseEntry()
    entry.title = df_dict.get('title')
    entry.publication = df_dict.get('publisher')
    entry.year = df_dict.get('year')
    entry.volume = df_dict.get('volume')
    entry.issue = df_dict.get('issue')
    entry.pages = df_dict.get('pages')
    entry.keywords = df_dict.get('keywords')
    entry.abstract = df_dict.get('abstract')
    entry.notes = df_dict.get('notes')
    entry.pubmed_id = df_dict.get('pmid')
    entry.issn = df_dict.get('issn')

    # Formatting
    if entry.year is not None:
        entry.year = str(entry.year)
    if entry.keywords is not None and isinstance(entry.keywords, list):
        entry.keywords = ', '.join(entry.keywords)

    entry.authors = []
    json_authors = df_dict.get('authors')
    if json_authors is not None:
        for auth in json_authors:
            author = obj.BaseAuthor()
            #TODO: This creates extra space if the first or last name is missing
            name = ' '.join([auth.get('first_name',''), auth.get('last_name','')])
            author.name = name
            entry.authors.append(author)

    ids = df_dict.get('identifiers')
    if ids is not None:
        if 'doi' in ids.keys():
            entry.doi = ids.get('doi')
            paper_info.doi = ids.get('doi')

    paper_info.entry = entry

    return paper_info


def _mendeley_json_to_paper_info(json):
    """
    
    See Also
    --------
    
    """
    
    #JAH TODO: PaperInfo is coming from pypub but it should come from library_db
    #JAH TODO: We want to store a unique id here ...
    
    import pdb
    pdb.set_trace()
    
    paper_info = PaperInfo()

    #TODO: obj needs to be clarified as well
    entry = obj.BaseEntry()
    entry.title = json.get('title')
    entry.publication = json.get('publisher')
    entry.year = json.get('year')
    entry.volume = json.get('volume')
    entry.issue = json.get('issue')
    entry.pages = json.get('pages')
    entry.keywords = json.get('keywords')
    entry.abstract = json.get('abstract')
    entry.notes = json.get('notes')

    entry.authors = []
    json_authors = json.get('authors')
    if json_authors is not None:
        for auth in json_authors:
            author = obj.BaseAuthor()
            name = ' '.join([auth.get('first_name',''), auth.get('last_name','')])
            author.name = name
            entry.authors.append(author)

    #TODO: DOI must be canonical, although we can check this in the paper_db
    ids = json.get('identifiers')
    if ids is not None:
        if 'doi' in ids.keys():
            entry.doi = ids.get('doi')
            paper_info.doi = ids.get('doi')
        if 'pmid' in ids.keys():
            entry.pubmed_id = ids.get('pmid')

    #It is not clear what this is doing ...
    paper_info.entry = entry

    return paper_info
