

from sqlalchemy import Column, String, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


#Arrays
#- Authors
#- Keywords
#- Tags

Base = declarative_base()

#Local Imports
#-------------------
from . import config


engine = create_engine('sqlite:///:memory:', echo=True)

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

    def get_session(self):
        Session = sessionmaker()
        Session.configure(bind=self.engine)
        session = Session()
        return session

class DocumentContributors(Base):
    __tablename__ = 'DocumentContributors'

    id = Column(Integer, primary_key=True)
    documentId = Column(Integer, ForeignKey('Documents.id'), nullable=False)
    contribution = Column(String, nullable=False)
    #Known contributor roles:
    #Authors - 'DocumentAuthor'
    #Editors - 'DocumentEditor'
    #Reporters -
    #


    firstNames = Column(String)
    lastName = Column(String)

    def __init__(self,contribution,data):
        """


        :param contribution: Depends on where entered but may be an an author
        or editor or any other person/role associated with the doc
        :param data: Dictionary containing first and last name
        :type data: dict
        """
        self.contribution = contribution
        self.firstNames = data['first_name']
        self.lastName = data['last_name']


#DocumentDetailsBase #7749
#DocumentFields => 1:24 - integers and names associated
#                           Where is this used????

#DocumentFiles
class DocumentFiles(Base):
    __tablename__ = 'DocumentFiles'

    documentId = Column(Integer, ForeignKey('Documents.id'), nullable=False)
    hash = Column(String(40), nullable=False, index=True),
    unlinked = Column(Boolean, nullable=False),
    downloadRestricted = Column(Boolean, nullable=False, default=False)
    remoteFileUuid = Column(String(38),nullable=False,default=u"")

#DocumentFolders - doc id, folder id, status????
#DocumentFoldersBase - doc id, folder id

#Document Keywords
class DocumentKeywords(Base_Internal):
    __tablename__ = 'DocumentKeywords'

    documentId = Column(Integer, ForeignKey('Documents.id'), nullable=False)
    keyword = Column(String, primary_key=True, nullable=False)

#DocumentNotes  #empty
#DocumentReferences #empty

class DocumentTags(Base):
    __tablename__ = 'DocumentTags'

    documentId = Column(Integer, ForeignKey('Documents.id'), nullable=False)
    tag = Column(String, primary_key=True, nullable=False)

class DocumentUrls(Base):
    __tablename__ = 'DocumentUrls'

    documentId = Column(Integer, ForeignKey('Documents.id'), nullable=False)
    position = Column(Integer, primary_key=True, nullable=False)
    url = Column(String, nullable=False)

#DocumentVersion???
#       - this is a timestamp - of what?????
#       - created, modified?
#       ?? what's not in the document????

#DocumentZotero - empty

class Document(Base):
    __tablename__ = 'Documents'

    contributors = relationship('DocumentContributors', cascade="all, delete-orphan")
    #Not sure how this should be handled ...
    #- If we don't download files, but only know that they exist ...
    files = relationship('DocumentFiles', cascade="all, delete-orphan")
    keywords = relationship('DocumentKeywords', cascade="all, delete-orphan")
    tags = relationship('DocumentTags', cascade="all, delete-orphan")
    urls = relationship('DocumentUrls', cascade="all, delete-orphan")

    #Renames and Actions
    #-------------------
    #identifiers - need to move up to main
    #authors - TO 'contributors'
    #source - 'publication'
    #websites - TO 'urls'
    #created - 'added'
    #file_attached??? - not present
    #   - store
    #profile_id - add
    #last_modified => 'lastUpdate'
    #tags => TO 'tags'
    #


    #???? keywords - how to push to list?
    #


    abstract = Column(String)
    added = Column(Integer)
    advisor = Column(String)
    applicationNumber = Column(String)
    articleColumn = Column(String)
    arxivId = Column(String)
    chapter = Column(String)
    citationKey = Column(String)
    city = Column(String)
    code = Column(String)
    codeNumber = Column(String)
    codeSection = Column(String)
    codeVolume = Column(String)
    committee = Column(String)
    confirmed = Column(Integer) #???? What is this, true or false
    #Looks like it is false when deletion is pending

    counsel = Column(String)
    country = Column(String)
    dateAccessed = Column(String)
    #I think this may be when last read ???
    day = Column(Integer)
    deduplicated = Column(Integer)
    deletionPending = Column(Integer)
    department = Column(String)
    doi = Column(String)
    edition = Column(String)
    favourite = Column(Integer)
    genre = Column(String)
    hideFromMendeleyWebIndex = Column(Integer)
    id = Column(Integer, primary_key=True)
    importer = Column(String)
    #ManualImporter
    #PDFImporter
    #UnkknowImporter
    institution = Column(String)
    internationalAuthor = Column(String)
    internationalNumber = Column(String)
    internationalTitle = Column(String)
    internationalUserType = Column(String)
    isbn = Column(String)
    issn = Column(String)
    issue = Column(String)
    language = Column(String)
    lastUpdate = Column(String)
    #All null in my DB

    legalStatus = Column(String)
    length = Column(String)
    medium = Column(String)
    modified = Column(Integer)
    month = Column(Integer)
    note = Column(String)
    originalPublication = Column(String)
    #all null

    owner = Column(String)
    pages = Column(String)
    pmid = Column(BigInteger)
    privacy = Column(String)
    #PublishedDocument - when one of my publications
    #NormalDocument
    publicLawNumber = Column(String)
    publication = Column(String)
    publisher = Column(String)
    read = Column(Integer)
    reprintEdition = Column(String)
    revisionNumber = Column(String)
    reviewedArticle = Column(String)
    sections = Column(String)
    series = Column(String)
    seriesEditor = Column(String)
    seriesNumber = Column(String)
    session = Column(String)
    shortTitle = Column(String)
    sourceType = Column(String)
    #Perhaps the original type????

    title = Column(String)
    type = Column(String) #Journal, Book Section, etc.
    uuid = Column(String, nullable=False)  # unique
    userType = Column(String)
    #thesis (only 1 row has this, all others null)
    volume = Column(String)
    year = Column(Integer)

    def __init__(self,data):
        pass



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

#TODO: Indices
