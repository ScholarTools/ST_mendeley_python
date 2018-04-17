# -*- coding: utf-8 -*-
"""
Contains all custom errors called within the mendeley_python package.
"""

class UserCodeError(Exception):
    pass

class InvalidConfig(Exception):
    """
        Used to indicate that either a config is missing or that something 
        is incorrect about the config specification.
    """
    pass

class OptionalLibraryError(Exception):
    pass

class UnsupportedEntryTypeError(Exception):
    pass

#------------------- API -------------------------------
class CallFailedException(Exception):
    pass

# ----------------- User Library Errors ----------------
class UserLibraryError(Exception):
    pass
    
class DocNotFoundError(UserLibraryError):
    pass
    
#class DOINotFoundError(MissingDocError):
#    pass

#class DocNotFoundError(MissingDocError):
#    pass

class DuplicateDocumentError(UserLibraryError):
    pass



class PDFError(Exception):
    pass

class AuthException(Exception):
    pass


# ----------------- Database Errors --------------------
class MultipleDoiError(Exception):
    pass

class DatabaseError(Exception):
    pass
