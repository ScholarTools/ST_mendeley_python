"""
Status thus far:
1) Adding fresh documents works
2) DONE No support yet for checking if document exists
3) Have not added indices yet to make querying faster
4) Needs to be tied into the client library code

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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine


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


Base = declarative_base()


#Tables
#--------------------------------------------------
#CanonicalDocuments ???
#DataCleaner
#DocumentCanonicalIds #349



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
        #??? How do we want do manage Folders???

    def add_documents(self,data):
        #- modified documents???
        #       - unknown

        if not data:
            return {'modified':[],'new':[]}


        doc_ids_modified = []
        doc_ids_new = []
        #TODO: What if we have a conflict?
        session = self.get_session()
        for i, doc in enumerate(data):

            temp = session.query(Document.last_modified).filter(Document.id == doc['id']).first()

            if temp:
                #Document already exists
                #'last_modified' example:
                #'2017-03-13T08:34:13.640Z'
                format_str = '%Y-%m-%dT%H:%M:%S.%f%z'
                db_datetime = datetime.strptime(temp[0],format_str)
                new_datetime = datetime.strptime(doc['last_modified'],format_str)
                if db_datetime == new_datetime:
                    #Don't do anything
                    continue
                elif new_datetime > db_datetime:
                    #Modified, update with new version
                    doc_ids_modified.append(doc['id'])
                    session.query(Document).filter_by(id=doc['id']).delete()
                else:
                    #Db version is newer, this should never happen ...
                    #We might want to throw an error here
                    continue
            else:
                doc_ids_new.append(doc['id'])

            temp_doc = Document(doc)
            session.add(temp_doc)

        #All docs added ... commit and close
        session.commit()
        session.close()

        return {'modified':doc_ids_modified,'new':doc_ids_new}

    def get_session(self) -> Session:
        Session = sessionmaker()
        Session.configure(bind=self.engine)
        session = Session()
        return session

class DocumentContributors(Base):
    __tablename__ = 'DocumentContributors'

    #Apparently the ORM needs a primary key ...
    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey('Documents.local_id'), nullable=False, index=True)
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

class DocumentUrls(Base):
    __tablename__ = 'DocumentUrls'

    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey('Documents.local_id'), nullable=False, index=True)
    url = Column(String, nullable=False)
    #__table_args__ = (PrimaryKeyConstraint('doc_id', 'url'),)

    def __init__(self,value):
        self.url = value

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
    authors = relationship('DocumentContributors', cascade="all, delete-orphan")
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
    editors = relationship('DocumentContributors', cascade="all, delete-orphan")
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
    translators = relationship('DocumentContributors', cascade="all, delete-orphan")
    type = Column(String)  # Journal, Book Section, etc.
    user_context = Column(String(255))
    volume = Column(String(10))
    websites = relationship('DocumentUrls', cascade="all, delete-orphan")
    year = Column(Integer)


    #Jim Entries
    is_dirty = Column(Boolean,default=False)

    def __init__(self,data: dict):
        #bill
        #case
        #computer_program

        #pop identifiers
        #
        #authors
        #
        cls_ = type(self)
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
                    import pdb
                    pdb.set_trace()
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
    def __repr__(self):

        pv = ['pmid', self.pmid, 'doi', self.doi, 'issn', self.issn,
              'isbn', self.isbn, 'arxiv', self.arxiv]
        return utils.property_values_to_string(pv)

        abstract = Column(String(10000))
        accessed = Column(String)
        arxiv = Column(String, index=True)
        authored = Column(Boolean)
        authors = relationship('DocumentContributors',
                               cascade="all, delete-orphan")
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
                               cascade="all, delete-orphan")
        file_attached = Column(Boolean)
        folder_uuids = relationship('FolderUUIDs',
                                    cascade="all, delete-orphan")
        genre = Column(String(255))
        group_id = Column(String)
        hidden = Column(Boolean)
        id = Column(String, nullable=False, unique=True, index=True)
        institution = Column(String(255))
        isbn = Column(String)
        issn = Column(String)
        issue = Column(String(255))
        keywords = relationship('DocumentKeywords',
                                cascade="all, delete-orphan")
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
                                   cascade="all, delete-orphan")
        type = Column(String)  # Journal, Book Section, etc.
        user_context = Column(String(255))
        volume = Column(String(10))
        websites = relationship('DocumentUrls', cascade="all, delete-orphan")
        year = Column(Integer)






        pass
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


