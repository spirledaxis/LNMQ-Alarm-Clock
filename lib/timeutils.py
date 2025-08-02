def daynum_to_daystr(daynum):
    if daynum == 7:
        return 'sunday'
    elif daynum == 1:
        return 'monday'
    elif daynum == 2:
        return 'tuesday'
    elif daynum == 3:
        return 'wednesday'
    elif daynum == 4:
        return 'thursday'
    elif daynum == 5:
        return 'friday'
    elif daynum == 6:
        return 'saturday'
    else:
        raise ValueError('Not a valid daynum, should be between 0-6')

def monthnum_to_monthstr(monthnum):
    if monthnum == 1:
        return 'january'
    elif monthnum == 2:
        return 'february'
    elif monthnum == 3:
        return 'march'
    elif monthnum == 4:
        return 'april'
    elif monthnum == 5:
        return 'may'
    elif monthnum == 6:
        return 'june'
    elif monthnum == 7:
        return 'july'
    elif monthnum == 8:
        return 'august'
    elif monthnum == 9:
        return 'september'
    elif monthnum == 10:
        return 'october'
    elif monthnum == 11:
        return 'november'
    elif monthnum == 12:
        return 'december'
    else:
        raise ValueError('Not a valid monthnum, should be between 0-6')

def convert_to_ampm(hour):
    """convert military hour to hour, also finds am/pm"""
    if hour > 12:
        ampm = 'pm'
        hour = hour - 12
    elif hour == 12:
        ampm = 'pm'
    elif hour == 0:
        ampm = 'am'
        hour = 12
    else:
        ampm = 'am'
    return hour, ampm

def to_military_time(hour, ampm):
    """
    Convert hour and 'am'/'pm' string to 24-hour military time.
    
    Args:
        hour (int): Hour in 12-hour format (1-12)
        ampm (str): 'am' or 'pm'
    
    Returns:
        int: Hour in 24-hour format (0-23)
    """
    if ampm.lower() == 'am':
        if hour == 12:
            return 0  # midnight
        else:
            return hour
    elif ampm.lower() == 'pm':
        if hour == 12:
            return 12  # noon
        else:
            return hour + 12
    else:
        raise ValueError("ampm must be 'am' or 'pm'")

