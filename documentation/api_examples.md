## API Walkthroughs ##

```python
from mendeley import API
api = API()



#Annotations
#--------------------------------



#Definitions
#--------------------------------



#Documents
#--------------------------------

#-- get() ------
docs = api.documents.get()


get_by_id()


#--- get_deleted() -----------





#--- create() --------------



create_from_file
delete
update
move_to_trash


#Library Documents Search
#-------------------------------
# Doesn't seem to be used, so seems to be broken

doc_set = api.documents.search(min_year=1980,max_year=1985,source='Journal of Urology')

#????? - doesn't work - invalid query
doc_set = api.documents.search(tag='Journal__JUrology',use_and=True,query='urethra')

#??????? - no results, why?
doc_set = api.documents.search(tag='Journal__JUrology')


#??????? - no results, why?
doc_set = api.documents.search(tag='ISD')
doc_set = api.documents.search(tag='isd')

#This worked
doc_set = api.documents.search(author='Ameri')






```
