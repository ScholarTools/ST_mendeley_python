"""
Status thus far:
1) Adding fresh documents works
2) DONE No support yet for checking if document exists
3) Have not added indices yet to make querying faster
4) Needs to be tied into the client library code

"""

"""
sqlalchemy
.__mapper__.iterate_properties
.__mapper__.c.keys()

"""

"""
    from mendeley import db_tables as db
    from mendeley import API

    m = API()
    db1 = db.DB('jimh@wustl.edu')
    docs_to_add = m.documents.get(limit=500,_return_type='json')
    db1.add_documents(docs_to_add)
"""

#Standard
import os
from datetime import datetime


#Third-Party
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, BigInteger
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, event

from sqlalchemy.orm.relationships import RelationshipProperty


#Arrays
#- Authors
#- Keywords
#- Tags

#Local Imports
#-------------------
from . import config
from . import utils
from .utils import get_truncated_display_string as td
from .utils import get_list_class_display as cld
from .utils import display_class


Base = declarative_base()


#Tables
#--------------------------------------------------
#CanonicalDocuments ???
#DataCleaner
#DocumentCanonicalIds #349


class AddDocsSummary():
    """
    Summarizes what happened when adding documents to the DB

    """

    def __init__(self):
        self.same = []
        self.modified = []
        self.new = []
        self.conflicted = []

    @property
    def n_added(self):
        return len(self.same) + self.n_different

    @property
    def n_different(self):
        return len(self.modified) + len(self.new) + len(self.conflicted)

    def merge(self,other:'AddDocsSummary'):
        self.same.extend(other.same)
        self.modified.extend(other.modified)
        self.new.extend(other.new)
        self.conflicted.extend(other.conflicted)

    def get_summary_string(self):
        return "{} added: {} no change, {} modified, {} new, {} conflicted".\
            format(self.n_added,len(self.same),len(self.modified),len(self.new),len(self.conflicted))

    def __repr__(self):
        return display_class(self,
                             [  'same', td(self.same),
                                'modified', td(self.modified),
                                'new', td(self.new),
                                'conflicted',td(self.conflicted),
                                'n_added', self.n_added,
                                'n_different',self.n_different])

class DB():

    def __init__(self,user_name=None):
        if user_name is None:
            #The client gets this from the api :/
            #TODO: How to resolve
            pass
        self.user_name = user_name
        root_path = config.get_save_root(['db'], True)
        save_name = utils.user_name_to_file_name(self.user_name) + '.sqlite'
        self.file_path = os.path.join(root_path, save_name)
        self.engine = create_engine('sqlite:///' + self.file_path)
        Base.metadata.create_all(bind=self.engine)

        self.Document = Document
        self.DocumentContributors = DocumentContributors
        self.DocumentKeywords = DocumentKeywords
        self.DocumentTags = DocumentTags
        self.DocumentUrls = DocumentUrls
        self.Globals = Globals

        #??? How do we want do manage Folders???

    def add_documents(self,data,session=None,on_conflict='error',drop_time=None)->AddDocsSummary:
        """

        Parameters
        ----------
        on_conflict : {'web','local','cmd','gui','error'}
        drop_time : string
            This is a workaround for queries that only

        Returns
        -------
        dict
            {'modified':doc_ids_modified,'new':doc_ids_new}
        """
        #- modified documents???
        #       - unknown
        #

        r = AddDocsSummary()

        if not data:
            return r


        doc_ids_modified = []
        doc_ids_new = []
        doc_ids_conflicted = []
        doc_ids_same = []

        if session is None:
            session = self.get_session()
            close_session = True
        else:
            close_session = False

        for i, doc in enumerate(data):

            if doc['last_modified'] == drop_time:
                doc_ids_same.append(doc['id'])
                continue

            #Note doc is a dictionary, not an object ...

            add_new_doc = True
            temp = session.query(Document.last_modified,Document.is_dirty,Document.local_id)\
                .filter(Document.id == doc['id']).first()

            if temp: # Document already exists
                if temp.is_dirty:
                    doc_ids_conflicted.append(doc['id'])
                    #For right now, we
                    temp_doc = Document(doc)
                    dirty_doc = session.query(Document).filter(
                        Document.local_id == temp.local_id).first()

                    info = DocumentConflictSummary(dirty_doc,temp_doc)

                    #For right now, we'll only support using remote

                    session.delete(dirty_doc)
                    session.flush()

                    #TODO: Fix this ...
                    """
                    if on_conflict == 'error':
                        pass
                    elif on_conflict == 'cmd':
                        pass
                    elif on_conflict == 'gui':
                        pass
                    import pdb
                    pdb.set_trace()
                    """
                else:
                    #'last_modified' example:
                    #'2017-03-13T08:34:13.640Z'
                    #TODO: Push this into the document ...
                    #string_to_datetime
                    format_str = '%Y-%m-%dT%H:%M:%S.%f%z'
                    db_datetime = datetime.strptime(temp.last_modified,format_str)
                    new_datetime = datetime.strptime(doc['last_modified'],format_str)
                    if db_datetime == new_datetime:
                        #I think this only happens due to a problem with
                        #modified times returning >= instead of >
                        #so we have 1 doc that is the same
                        doc_ids_same.append(doc['id'])
                        continue
                    elif new_datetime > db_datetime:
                        #Modified, update with new version
                        #TODO: Not sure if local_id is quicker or not
                        doc_ids_modified.append(doc['id'])
                        session.query(Document).filter_by(id=doc['id']).delete()
                        session.flush()
                    else:
                        raise Exception("Code error, DB version of doc newer but not marked as dirty")
                        #Db version is newer, this should never happen ...
                        #We might want to throw an error here
            else:
                doc_ids_new.append(doc['id'])

            if add_new_doc:
                temp_doc = Document(doc)
                session.add(temp_doc)

        #All docs added ... commit and close
        if close_session:
            session.commit()
            session.close()

        r.conflicted = doc_ids_conflicted
        r.modified = doc_ids_modified
        r.new = doc_ids_new
        r.same = doc_ids_same

        return r

    def get_session(self) -> Session:
        Session = sessionmaker()
        Session.configure(bind=self.engine)
        session = Session()
        return session

class DocumentContributors(Base):
    __tablename__ = 'DocumentContributors'

    #Apparently the ORM needs a primary key ...
    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey('Documents.local_id'), nullable=False,
                    index=True)
    contribution = Column(String, nullable=False)

    #Known contributor roles:
    #Authors - 'DocumentAuthor'
    #Editors - 'DocumentEditor'
    #Reporters -
    #
    #first_name = Column(String,default="")
    first_name = Column(String)
    last_name = Column(String)
    #We ran into the problem of the same author on the same article
    #- F Obal and F Obal Jr
    #__table_args__ = (PrimaryKeyConstraint('doc_id', 'contribution',
    #                                       'first_name', 'last_name'),)

    #scopus_author_id = Column(String)

    def __init__(self,contribution,data):
        """
        :param contribution: Depends on where entered but may be an an author
        or editor or any other person/role associated with the doc
        :param data: Dictionary containing first and last name
        :type data: dict
        """
        self.contribution = contribution
        #Apparently this is not always present ...
        if 'first_name' in data:
            self.first_name = data['first_name']

        self.last_name = data['last_name']

    def as_dict(self):
        dict_ = {}
        for key in self.__mapper__.c.keys():
            temp = getattr(self, key)
            if temp is not None:
                dict_[key] = temp

        dict_.pop('doc_id',None)
        dict_.pop('id',None)
        dict_.pop('contribution',None)

        return dict_


#DocumentDetailsBase #7749
#DocumentFields => 1:24 - integers and names associated
#                           Where is this used????

#DocumentFiles
"""
class DocumentFiles(Base):
    __tablename__ = 'DocumentFiles'

    doc_id = Column(Integer, ForeignKey('Documents.local_id'), nullable=False)
    hash = Column(String(40), nullable=False, index=True),
    unlinked = Column(Boolean, nullable=False),
    download_restricted = Column(Boolean, nullable=False, default=False)
    remote_fil_uuid = Column(String(38),nullable=False,default=u"")
"""

#DocumentFolders - doc id, folder id, status????
#DocumentFoldersBase - doc id, folder id

#Document Keywords
class DocumentKeywords(Base):
    __tablename__ = 'DocumentKeywords'

    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey('Documents.local_id'), nullable=False, index=True)
    keyword = Column(String, nullable=False)
    #__table_args__ = (PrimaryKeyConstraint('doc_id', 'keyword'),)
    def __init__(self,value):
        self.keyword = value

    def as_dict(self):
        return self.keyword

#DocumentNotes  #empty
#DocumentReferences #empty

class DocumentTags(Base):
    __tablename__ = 'DocumentTags'

    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey('Documents.local_id'), nullable=False, index=True)
    tag = Column(String, nullable=False)
    #__table_args__ = (PrimaryKeyConstraint('doc_id', 'tag'),)

    def __init__(self,value):
        self.tag = value

    def as_dict(self):
        return self.tag

class DocumentUrls(Base):
    __tablename__ = 'DocumentUrls'

    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey('Documents.local_id'), nullable=False, index=True)
    url = Column(String, nullable=False)
    #__table_args__ = (PrimaryKeyConstraint('doc_id', 'url'),)

    def __init__(self,value):
        self.url = value

    def as_dict(self):
        return self.url

#DocumentVersion???
#       - this is a timestamp - of what?????
#       - created, modified?
#       ?? what's not in the document????

#DocumentZotero - empty

class FolderUUIDs(Base):
    __tablename__ = 'FolderUUIDs'

    id = Column(Integer, primary_key=True)
    folder_uuid = Column(String(36))
    doc_id = Column(Integer, ForeignKey('Documents.local_id'), nullable=False, index=True)
    #__table_args__ = (PrimaryKeyConstraint('doc_id', 'folder_uuid'),)

    def __init__(self,value):
        self.folder_uuid = value


class Globals(Base):
    __tablename__ = 'Globals'

    id = Column(Integer, primary_key=True)
    doc_modified_since = Column(String)
    doc_deleted_since = Column(String)
    doc_trashed_since = Column(String)
    file_added_since = Column(String)
    file_deleted_since = Column(String)
    annotations_modified_since = Column(String)
    annotations_deleted_since = Column(String)

class Document(Base):
    __tablename__ = 'Documents'

    # https://dev.mendeley.com/methods/#core-document-attributes
    #This is more recent and seems right
    #https: // api.mendeley.com / apidocs / docs  # !/documents/getDocuments

    #Core Attributes
    #-------------------------------------
    #From:

    local_id = Column(Integer, primary_key=True)

    abstract = Column(String(10000))
    accessed = Column(String)
    arxiv = Column(String, index=True)
    authored = Column(Boolean)
    authors = relationship('DocumentContributors',
                           cascade="all, delete-orphan",
                           primaryjoin="and_(Document.local_id==DocumentContributors.doc_id, "
                                       "DocumentContributors.contribution=='authors')"
                           )
    chapter = Column(String(10))
    citation_key = Column(String(255))
    city = Column(String(255))
    code = Column(String(255))
    confirmed = Column(Boolean)
    country = Column(String(255))
    created = Column(String)
    day = Column(Integer)
    department = Column(String(255))
    doi = Column(String, index=True)
    edition = Column(String)
    editors = relationship('DocumentContributors',
                           cascade="all, delete-orphan",
                           primaryjoin="and_(Document.local_id==DocumentContributors.doc_id, "
                                       "DocumentContributors.contribution=='editors')"
                           )
    file_attached = Column(Boolean)
    folder_uuids = relationship('FolderUUIDs', cascade="all, delete-orphan")
    genre = Column(String(255))
    group_id = Column(String)
    hidden = Column(Boolean)
    id = Column(String, nullable=False, unique=True, index=True)
    institution = Column(String(255))
    isbn = Column(String)
    issn = Column(String)
    issue = Column(String(255))
    keywords = relationship('DocumentKeywords', cascade="all, delete-orphan")
    language = Column(String(255))
    last_modified = Column(String)
    medium = Column(String)
    month = Column(Integer)
    notes = Column(String)
    pages = Column(String(50))
    patent_application_number = Column(String(255))
    patent_legal_status = Column(String(255))
    patent_owner = Column(String(255))
    pmid = Column(BigInteger, index=True)
    private_publication = Column(Boolean)
    profile_id = Column(String)
    publisher = Column(String(255))
    read = Column(Boolean)
    reprint_edition = Column(String(10))
    revision = Column(String(255))
    scopus = Column(String)
    series = Column(String(255))
    series_editor = Column(String(255))
    series_number = Column(String(255))
    short_title = Column(String(50))
    source = Column(String(255))
    source_type = Column(String(255))
    ssrn = Column(String)
    starred = Column(Boolean)
    tags = relationship('DocumentTags', cascade="all, delete-orphan")
    title = Column(String(255))
    translators = relationship('DocumentContributors',
                               cascade="all, delete-orphan",
                               primaryjoin="and_(Document.local_id==DocumentContributors.doc_id, "
                                           "DocumentContributors.contribution=='translators')"
                               )
    type = Column(String)  # Journal, Book Section, etc.
    user_context = Column(String(255))
    volume = Column(String(10))
    websites = relationship('DocumentUrls', cascade="all, delete-orphan")
    year = Column(Integer)


    #Jim Entries
    #----------------------------------------------------
    is_new   = Column(Boolean,default=False)
    is_dirty = Column(Boolean,default=False)
    is_trashed = Column(Boolean,default=False)
    #Note, we'll drop deleted entries, but we need to keep track of what's been
    #deleted locally but not synced
    is_deleted = Column(Boolean,default=False)

    def __init__(self, data: dict):
        #bill
        #case
        #computer_program

        #pop identifiers
        #
        #authors
        #
        cls_ = type(self)
        self.is_dirty = False #Needed for instances that only live in memory
        for k,v in data.items():
            if not hasattr(cls_, k):
                if k == 'identifiers':
                    ids = data['identifiers']
                    for k2 in ids:
                        #Perhaps compare to known identifiers instead ...
                        #Not sure of speed of hasattr vs 'in' on smaller set
                        if hasattr(cls_, k2):
                            setattr(self, k2, ids[k2])
                        else:
                            raise TypeError(
                                "%r is an invalid keyword argument for %s" % (
                                    k2, cls_.__name__)
                            )
                else:
                    raise TypeError(
                        "%r is an invalid keyword argument for %s" % (
                        k, cls_.__name__)
                    )
            elif k == 'authors':
                self.authors = [DocumentContributors('authors', x) for x in data[k]]
            elif k == 'editors':
                self.editors = [DocumentContributors('editors', x) for x in data[k]]
            elif k == 'translators':
                self.translators = [DocumentContributors('translators',x) for x in data[k]]
            elif k == 'tags':
                self.tags = [DocumentTags(x) for x in data[k]]
            elif k == 'keywords':
                self.keywords = [DocumentKeywords(x) for x in data[k]]
            elif k == 'websites':
                self.websites = [DocumentUrls(x) for x in data[k]]
            elif k == 'folder_uuids':
                self.folder_uuids = [FolderUUIDs(x) for x in data[k]]
            else:
                setattr(self, k, data[k])

    """
    #- This occurs both for existing and for new
    #- Would want only for existing
    #- Also, need to be able to commit without marking dirty so I
    # changed to not using this ...
    
    @staticmethod
    def mark_dirty(mapper, connection, target):
        target.is_dirty = True

    @classmethod
    def __declare_last__(cls):
        # get called after mappings are completed
        # http://docs.sqlalchemy.org/en/rel_0_7/orm/extensions/declarative.html#declare-last
        event.listen(cls, 'before_insert', cls.mark_dirty)
    """

    #is_trashed = Column(Boolean,default=False)
    #Note, we'll drop deleted entries, but we need to keep track of what's been
    #deleted locally but not synced
    #is_deleted = Column(Boolean,default=False)

    def delete(self):
        self.is_deleted = True
        self.commit()

    def trash(self):
        self.is_trashed = True
        self.commit()

    def commit(self,_is_dirty=True):
        session = Session.object_session(self)
        self.is_dirty = _is_dirty
        session.commit()

    def as_dict(self):
        """
        Converts internals to dictionary
        #TODO
        #1) Handle returning all params

        """

        dict_ = {}
        for key in self.__mapper__.c.keys():
            temp = getattr(self, key)
            if temp is not None:
                dict_[key] = temp

        #No need to see this ...
        dict_.pop('is_dirty',None)
        dict_.pop('local_id',None)
        dict_.pop('is_trashed',None)
        dict_.pop('is_deleted',None)

        fields = ['authors','editors','translators','tags','keywords','websites']
        for field in fields:
            temp = getattr(self,field)
            if temp:
                dict_[field] = [x.as_dict() for x in temp]

        ids = {}
        id_fields = ['doi','pmid','issn','isbn','arxiv']
        for key in id_fields:
            if key in dict_:
                ids[key] = dict_[key]
                del dict_[key]

        if len(ids) > 0:
            dict_['identifiers'] = ids

        return dict_

    def __repr__(self):

        flatten = lambda x: td(str([y.as_dict() for y in x]))

        pv = ['abstract',self.abstract,
              'accessed',self.accessed,
              'arxiv',self.arxiv,
              'authored',self.authored,
              'authors',flatten(self.authors),
              'chapter',self.chapter,
              'citation_key',self.citation_key,
              'city',self.city,
              'code',self.code,
              'confirmed',self.confirmed,
              'country',self.country,
              'created',self.created,
              'day',self.day,
              'department',self.department,
              'doi',self.doi,
              'edition',self.edition,
              'editors',flatten(self.editors),
              'file_attached',self.file_attached,
              'folder_uuids',flatten(self.folder_uuids),
              'genre',self.genre,
              'group_id',self.group_id,
              'hidden',self.hidden,
              'id',self.id,
              'institution',self.institution,
              'isbn',self.isbn,
              'issn',self.issn,
              'issue',self.issue,
              'keywords',flatten(self.keywords),
              'language',self.language,
              'last_modified',self.last_modified]
        return utils.property_values_to_string(pv)


        """
        medium = Column(String)
        month = Column(Integer)
        notes = Column(String)
        pages = Column(String(50))
        patent_application_number = Column(String(255))
        patent_legal_status = Column(String(255))
        patent_owner = Column(String(255))
        pmid = Column(BigInteger, index=True)
        private_publication = Column(Boolean)
        profile_id = Column(String)
        publisher = Column(String(255))
        read = Column(Boolean)
        reprint_edition = Column(String(10))
        revision = Column(String(255))
        scopus = Column(String)
        series = Column(String(255))
        series_editor = Column(String(255))
        series_number = Column(String(255))
        short_title = Column(String(50))
        source = Column(String(255))
        source_type = Column(String(255))
        ssrn = Column(String)
        starred = Column(Boolean)
        tags = relationship('DocumentTags', cascade="all, delete-orphan")
        title = Column(String(255))
        translators = relationship('DocumentContributors',
                                   cascade="all, delete-orphan")
        type = Column(String)  # Journal, Book Section, etc.
        user_context = Column(String(255))
        volume = Column(String(10))
        websites = relationship('DocumentUrls', cascade="all, delete-orphan")
        year = Column(Integer)
        """



#EventAttributes
#EventLog

#   Might be nice to implement eventually ...
#----------------------
#FileHighlightRects
#FileHighlights
#FileNotes

#FileReferenceCount

#TODO: Files
#TODO: Folders
#Groups : empty
#HtmlLocalStorage: empty
#ImportHistory:
#LastReadStates:
#NotDuplicates
#Profiles
#RemoteDocumentNotes
#RemoteDocuments:7797
#RemotefileHighlights:17442
#RemoteFileNotes
#RemoteFolders:490
#Resources: empty
#RunsSinceLastCleanup
#SchemaVersion
#Settings
#Stats - empty
#SyncTokens - This looks
#like when the action was last performed ...
"""
"0"	"AnnotationsDeleted"	"2018-04-19T14:17:55.000Z"
"0"	"AnnotationsModified"	"2018-04-19T14:17:53.000Z"
"0"	"FilesDeleted"	"2018-04-19T14:17:28.000Z"
"0"	"FilesAdded"	"2018-04-19T14:17:26.000Z"
"0"	"DocumentsDeleted"	"2018-04-19T14:17:22.000Z"
"0"	"DocumentsTrashed"	"2018-04-19T14:17:22.000Z"
"0"	"DocumentsModified"	"2018-04-19T14:17:19.000Z"
"""
#ZoteroLastSync - empty
#sqlite_sequence (table)
"""
"Groups"	"0"
"Folders"	"490"
"Documents"	"7805"
"DocumentFields"	"24"
"FileHighlights"	"17642"
"FileHighlightRects"	"19895"
"FileNotes"	"2738"
"EventLog"	"6924"
"CanonicalDocuments"	"361"
"""

class DocumentConflictSummary(object):

    def __init__(self,o1,o2):

        diffs = {}
        #d1 - local
        #d2 - web

        mapper = inspect(Document)
        attrs = mapper.attrs #type: sqlalchemy.util._collections.ImmutableProperties

        for attr in attrs:
            key = attr.key
            v1 = getattr(o1,key)
            v2 = getattr(o2,key)

            if isinstance(attr,RelationshipProperty):
                d1 = [x.as_dict() for x in v1]
                d2 = [x.as_dict() for x in v2]
                if d1 != d2:
                    diffs[key] = PropertyDiffSummary(key,d1,d2,True)
            else:
                if v1 != v2 and key not in ['local_id','is_dirty','last_modified']:
                    diffs[key] = PropertyDiffSummary(key,v1,v2,False)

        self.diffs = diffs
        self.n_diffs = len(diffs)

    def get_summary_string(self):
        if self.n_diffs == 0:
            str = 'No conflicts found'
        else:
            str = '{} conflicts found\n--------------------------------'.format(self.n_diffs)
            for key in self.diffs:
                str += '\n'
                str += self.diffs[key].get_summary_string()

        return str

class PropertyDiffSummary(object):
    """
    Holds info on a difference

    Not sure exactly what I want here

    See Also
    --------
    DocumentConflictSummary

    """

    def __init__(self,key,v1,v2,is_complex):
        #local
        #web
        self.key = key
        self.v1 = v1
        self.v2 = v2
        self.is_complex = is_complex

    def get_summary_string(self):

        s1 = td(self.v1)
        s2 = td(self.v2)

        str = "{}:\n  local: {}\n  remote: {}".format(self.key,s1,s2)

        return str

def _string_to_datetime():
    pass
