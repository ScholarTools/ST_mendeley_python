# -*- coding: utf-8 -*-
"""
"""

import hashlib
import os

# BUF_SIZE is totally arbitrary, change for your app!
BUF_SIZE = 65536  # lets read stuff in 64kb chunks!

def get_file_hash(bytes_or_file_path):
    
    sha1 = hashlib.sha1()
    
    if os.path.exists(bytes_or_file_path):
        file_path = bytes_or_file_path
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                sha1.update(data)
    else:
        bytes = bytes_or_file_path
        sha1.update(bytes)
        
    return sha1

class _Quotes(str):
    pass

def quotes(input_value):
    if input_value is None:
        return None
    elif isinstance(3, int):
        return input_value
    else:
        return _Quotes(input_value)


def display_class(class_instance, pv):
    return '\n%s:\n\n' % type(class_instance) + property_values_to_string(pv,
                                                                          extra_indentation=4)


def property_values_to_string(pv, extra_indentation=0):
    """
    Parameters
    ----------
    pv : OrderedDict
        Keys are properties, values are values
    """

    # Max length

    keys = pv[::2]
    values = pv[1::2]
    values = ['"%s"' % x if isinstance(x, _Quotes) else x for x in values]

    key_lengths = [len(x) for x in keys]
    max_key_length = max(key_lengths) + extra_indentation
    space_padding = [max_key_length - x for x in key_lengths]
    key_display_strings = [' ' * x + y for x, y in zip(space_padding, keys)]

    str = u''
    for (key, value) in zip(key_display_strings, values):
        str += '%s: %s\n' % (key, value)

    return str


def get_list_class_display(value):
    """
    TODO: Go from a list of objects to:
    [class name] len(#)
    """
    if value is None:
        return 'None'
    elif isinstance(value, list):
        # Check for 0 length
        try:
            if len(value) == 0:
                return u'[??] len(0)'
            else:
                return u'[%s] len(%d)' % (
                value[0].__class__.__name__, len(value))
        except:
            import pdb
            pdb.set_trace()
            # run the code
    else:
        return u'<%s>' % (value.__class__.__name__)


def get_truncated_display_string(input_string: str, max_length: int = 30):
    """

    :param input_string:
    :param max_length:
    :return:
    """
    if input_string is None:
        return 'None'
    elif len(input_string) > max_length:
        return input_string[:max_length] + '...'
    else:
        return input_string

def float_or_none_to_string(x):
    if x is None:
        return 'None'
    else:
        return '%0.2f' % x

def user_name_to_file_name(user_name):
    """
    Provides a standard way of going from a user_name to something that will
    be unique (should be ...) for files

    NOTE: NO extensions are added

    See Also:
    utils.get_save_root
    """

    # Create a valid save name from the user_name (email)
    # ----------------------------------------------------------------------
    # Good enough for now ...
    # Removes periods from email addresses, leaves other characters
    return user_name.replace('.', '')


def get_unnasigned_json(json_data, populated_object):
    """
       Given an object which has had fields assigned to it, as well as the
       JSON dict from which these values were retrieved, this function returns
       a list of keys that were not used for populating the object.

       In order to match the attribute names and dictionary keys must have the
       same names.
    """
    if len(json_data) == 0:
        return {}
    else:
        temp_keys = populated_object.__dict__.keys()
        return dict((key, json_data[key]) for key in set(json_data) if key not in temp_keys)


def assign_json(json_data, field_name, optional=True, default=None):
    """
    This function can be used to make an assignment to an object. Since the
    majority of returned json repsonses contain optional fields.
    """

    if field_name in json_data:
        return json_data[field_name]
    elif optional:
        return default
    else:
        raise Exception("TODO: Fix me")
