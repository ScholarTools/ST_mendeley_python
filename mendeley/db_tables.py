from sqlalchemy import Column, String, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

#Arrays
#- Authors
#- Keywords
#- Tags

Base = declarative_base()

#Authors
#Editors
class DocumentContributors(Base):
    __tablename__ = 'DocumentContributors'

    id = Column(Integer, primary_key=True)
    documentId = Column(Integer, ForeignKey('Documents.id'), nullable=False)
    #DocumentEditor
    #DocumentAuthor
    contribution = Column(String, nullable=False)
    firstNames = Column(String)
    lastName = Column(String)

#DocumentFields => 1:24 - integers and names associated
#Where is this used????

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

#DocumentNotes
#??? Empty

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
#- this is a timestamp - of what?????
#- created, modified?
#?? what's not in the document????

class Document(Base):
    __tablename__ = 'Documents'

    #TODO: pointers to the arrays
    #- contributors
    #- keywords
    #- tags
    #-

    id = Column(Integer, primary_key=True)
    uuid = Column(String, nullable=False) #unique
    type = Column(String)
    read = Column(Integer)
    deduplicated = Column(Integer)
    confirmed = Column(Integer)
    favourite = Column(Integer)
    deletionPending = Column(Integer)
    importer = Column(String)
    note = Column(String)
    added = Column(Integer)
    abstract = Column(String)
    modified = Column(Integer)
    articleColumn = Column(String)
    advisor = Column(String)
    arxivId = Column(String)
    applicationNumber = Column(String)
    privacy = Column(String)
    title = Column(String)
    codeNumber = Column(String)
    code = Column(String)
    codeVolume = Column(String)
    codeSection = Column(String)
    chapter = Column(String)
    city = Column(String)
    citationKey = Column(String)
    department = Column(String)
    day = Column(Integer)
    edition = Column(String)
    doi = Column(String)
    counsel = Column(String)
    committee = Column(String)
    dateAccessed = Column(String)
    country = Column(String)
    internationalNumber = Column(String)
    internationalAuthor = Column(String)
    internationalUserType = Column(String)
    internationalTitle = Column(String)
    genre = Column(String)
    institution = Column(String)
    hideFromMendeleyWebIndex = Column(Integer)
    legalStatus = Column(String)
    lastUpdate = Column(String)
    medium = Column(String)
    length = Column(String)
    issn = Column(String)
    isbn = Column(String)
    language = Column(String)
    issue = Column(String)
    pmid = Column(BigInteger)
    publicLawNumber = Column(String)
    publication = Column(String)
    originalPublication = Column(String)
    month = Column(Integer)
    pages = Column(String)
    owner = Column(String)
    seriesEditor = Column(String)
    sections = Column(String)
    seriesNumber = Column(String)
    series = Column(String)
    reprintEdition = Column(String)
    publisher = Column(String)
    revisionNumber = Column(String)
    reviewedArticle = Column(String)
    userType = Column(String)
    year = Column(Integer)
    volume = Column(String)
    shortTitle = Column(String)
    session = Column(String)
    sourceType = Column(String)


#EventAttributes
#EventLog

#   Might be nice to implement eventually ...
#----------------------
#FileHighlightRects
#FileHighlights
#FileNotes

#FileReferenceCount

#TODO: Files
#------------------------
#hash
#localURL

#TODO: Folders

#TODO: LastReadStates