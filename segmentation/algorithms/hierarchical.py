import re
from bs4 import element
from .segment import Segment, SegmentClass
from .functions import cosine_similarity
from .densinometric import max_density

list_tags = ["ul", "ol", "dl"]
inline_elements = ["b", "big", "i", "small", "tt", "abbr", "acronym", "cite",
                   "code", "dfn", "em", "kbd", "strong", "samp", "var", "a",
                   "bdo", "br", "img", "map", "object", "q", "script", "span",
                   "sub", "sup", "button", "input", "label", "select", "textarea",
                   "cufontext", "cufon"]


def word_set(tag):
    """
    Returns a set of words from tag or NavigableString.
    @param tag: element.Tag or element.NavigableString
    @return: set of words
    """
    reg = "[^\W\d_]+"

    if isinstance(tag, element.Tag):
        found = re.findall(reg, tag.text, re.UNICODE)
    else:
        found = re.findall(reg, unicode(tag), re.UNICODE)
    return {i.lower() for i in found}


def change_tag(x):
    """
    Changes tag to a comparable representation.
    @param x: Tag or NavigableString
    @return: true if a tag, false otherwise
    """
    if isinstance(x, element.Tag):
        return x.name
    else:
        return "text"


def filter_tag(x, i):
    """
    Checks if to go into an element.
    @param x: Tag or NavigableString
    @return: true if a tag, false otherwise
    """
    if x == "text":
        return -2
    elif x in inline_elements:
        return -1
    else:
        return i


def sequence_compare(sq1, sq2):
    """
    Compare tag sequences.
    @param sq1: sequence 1
    @param sq2: sequence 2
    @return: True if similar or False otherwise
    """
    sq1_no = filter(lambda x: x != "text", sq1)
    sq2_no = filter(lambda x: x != "text", sq2)
    # print sq1_no
    # print sq2_no
    if len(sq1_no) == 0 or len(sq2_no) == 0:
        return False
    else:
        return sq1_no == sq2_no


def set_compare(s1, s2):
    """
   Compare word sets.
    @param s1: set 1
    @param s2: set 2
    @return: True if similar or False otherwise
    """
    return s1 == s2


def seq_order(seq):
    f = [filter_tag(seq[i], i) for i in range(len(seq))]
    return filter(lambda x: x != -2, f)


def cases(tags):
    """
    Analyze and check different cases.
    @param tags: all tags
    @return: sequence of ids to check
    """
    # check whether it is not to similar
    sets = map(lambda x: word_set(x.text), tags)

    if all(set_compare(x, sets[0]) for x in sets[1:]):
        return map(lambda sg: [Segment(sg, SegmentClass.STATIC)], tags), True

    sequences = map(lambda one: map(change_tag, one.children), tags)

    # compare all the sequences
    # if they are the same we need to check them
    if all(sequence_compare(sequences[0], seq) for seq in sequences[1:]) and (len(sequences[0]) != 0):

        # check if they contain any block level
        filtered = [seq_order(seq) for seq in sequences]

        if all(f == -1 for f in filtered[0]):
            return map(lambda sg: [Segment(sg, SegmentClass.DYNAMIC)], tags), True

        return filtered, False

    # otherwise, this is a segment
    else:
        return map(lambda sg: [Segment(sg, SegmentClass.DYNAMIC)], tags), True


def concurent_search(tags):
    """
    Main function for concurently searching the tree.
    @param tags: roots of the trees
    @return: list of segments
    """
    if all([hasattr(tag, "children") for tag in tags]):

        filtered, is_segment = cases(tags)
        if is_segment:
            return filtered
        else:
            rets = [[] for _ in xrange(len(tags))]
            for i in range(len(filtered[0])):
                if filtered[0][i] != -1:
                    cnvs = map(lambda x: tags[x].contents[filtered[x][i]], range(len(tags)))
                    cas = concurent_search(cnvs)
                    for r, c in zip(rets, cas):
                        r.extend(c)

            return rets
    else:
        return [[] for _ in xrange(len(tags))]


def grade(x):
    """
    Grades the segment.
    @param x: segment object
    """

    wrong = 0.0
    all_letters = 0.0

    for i in x.tags:
        reject = i.find_all(['a', 'time'])

        digit_reg = re.compile("\d", re.UNICODE)
        links_nums = sum([len(digit_reg.findall(j.text)) for j in reject])
        nums = len(digit_reg.findall(i.text))

        word_reg = re.compile("\w", re.UNICODE)
        links_all = sum([len(word_reg.findall(j.text)) for j in reject])

        all_letters += len(word_reg.findall(i.text))
        wrong += nums - links_nums + links_all
    if all_letters != 0:
        x.index = (1.0 - float(wrong) / float(all_letters)) * max_density(x.tags[0])#len(x.word_set())

    return x


def segment_compare(x, y):
    if x.sclass != y.sclass:
        return x.sclass - y.sclass
    else:
        dif = x.index - y.index
        if dif > 0.0:
            return 1
        elif dif < 0.0:
            return -1
        else:
            return 0


def tree_segmentation(base):
    """
    Top level structure segmentation algorithm.
    @param base: list of root tags to analyze
    @type base: list of bs4.element.Tag
    @return n lists of segments
    @rtype list of segmentation.Segment
    """
    if len(base) < 2:
        return None

    converted = concurent_search(base)
    graded = [map(grade, a) for a in converted]
    return [sorted(i, cmp=segment_compare, reverse=True) for i in graded]

