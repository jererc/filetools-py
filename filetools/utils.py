import re


def split_words(s, sep=r'[\W_]+'):
    return [w for w in re.split(sep, s) if w]

def compare_words(s1, s2):
    '''Get the percentage of common words.
    '''
    result = 0
    for sep in (r'[\W_]+', r'\D+'):
        w1 = split_words(s1.lower(), sep=sep)
        if w1:
            w2 = split_words(s2.lower())
            result += sum([1 for w in w1 if w in w2]) / float(len(w1))
    return result

def in_range(n, val_min=None, val_max=None):
    if val_min and n < val_min:
        return False
    elif val_max and n > val_max:
        return False
    return True
