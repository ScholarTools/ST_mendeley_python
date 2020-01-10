import sqlite3
conn = sqlite3.connect('example.db')
cur = conn.cursor()


#Arrays
#- Authors
#- Keywords
#- Tags

class

CREATE TABLE DocumentContributors( id INTEGER PRIMARY KEY, documentId INTEGER NOT NULL, contribution VARCHAR NOT NULL, firstNames VARCHAR, lastName VARCHAR NOT NULL )


Documents = """CREATE TABLE Documents ( id INTEGER PRIMARY KEY AUTOINCREMENT
, uuid VARCHAR NOT NULL UNIQUE , type VARCHAR, read INT, deduplicated INT
, confirmed INT, favourite INT, deletionPending INT, importer VARCHAR
, note VARCHAR, added INT, abstract VARCHAR, modified INT
, articleColumn VARCHAR, advisor VARCHAR, arxivId VARCHAR
, applicationNumber VARCHAR, privacy VARCHAR, title VARCHAR
, codeNumber VARCHAR, code VARCHAR, codeVolume VARCHAR
, codeSection VARCHAR, chapter VARCHAR, city VARCHAR
, citationKey VARCHAR, department VARCHAR, day INT, edition VARCHAR
, doi VARCHAR, counsel VARCHAR, committee VARCHAR, dateAccessed VARCHAR
, country VARCHAR, internationalNumber VARCHAR, internationalAuthor VARCHAR
, internationalUserType VARCHAR, internationalTitle VARCHAR, genre VARCHAR
, institution VARCHAR, hideFromMendeleyWebIndex INT, legalStatus VARCHAR
, lastUpdate VARCHAR, medium VARCHAR, length VARCHAR, issn VARCHAR
, isbn VARCHAR, language VARCHAR, issue VARCHAR, pmid BIGINT
, publicLawNumber VARCHAR, publication VARCHAR, originalPublication VARCHAR
, month INT, pages VARCHAR, owner VARCHAR, seriesEditor VARCHAR
, sections VARCHAR, seriesNumber VARCHAR, series VARCHAR
, reprintEdition VARCHAR, publisher VARCHAR, revisionNumber VARCHAR
, reviewedArticle VARCHAR, userType VARCHAR, year INT, volume VARCHAR
, shortTitle VARCHAR, session VARCHAR, sourceType VARCHAR)"""






cur.execute(Documents)
conn.commit() #commit needed
select()
c.close()
