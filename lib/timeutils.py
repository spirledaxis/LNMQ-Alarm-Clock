def daynum_to_daystr(daynum):
    if daynum == 0:
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


