import os
import sys
from datetime import datetime
import time


def resource_path(relative_path: str) -> str:
    """
    Returns the absolute path of a resource given its relative path.
    
    Args:
        relative_path (str): The relative path of the resource.
        
    Returns:
        str: The absolute path of the resource.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def dt_to_ts(dt: datetime) -> float:
    """
    Convert a datetime object to a Unix timestamp.

    Args:
        dt (datetime): The datetime object to be converted.

    Returns:
        float: The Unix timestamp representation of the datetime object.
    """
    return time.mktime(dt.timetuple())


def ts_to_dt(ts: float) -> datetime:
    """
    Convert a timestamp to a datetime object.
    
    Args:
        ts (float): The timestamp to convert.
        
    Returns:
        datetime: The datetime object corresponding to the timestamp.
    """
    return datetime.fromtimestamp(ts)


def get_app_data_path() -> str:
    """
    This function returns the path to the AppData directory for EULogger.

    Returns:
        str: The path to the AppData directory for EULogger.
    """
    path = os.path.join(os.sep, os.path.expanduser("~"), "AppData", "Local", "EULogger")
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def format_filename(fn: str) -> str:
    """
    Format the given filename by joining it with the application data path.

    Parameters:
        fn (str): The filename to be formatted.

    Returns:
        str: The formatted filename.
    """
    return os.path.join(get_app_data_path(), fn)
