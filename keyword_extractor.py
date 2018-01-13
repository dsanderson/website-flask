import json
import random
import copy
import units
import re
import numpy as np

def grab_word_vectors(keywords, data, window=[-5, 5]):
    vecs = []
    for part in data:
        desc = part['text']
        desc_array = desc.lower().split()
        for i, w in enumerate(desc_array):
            if w.strip() in keywords:
                left = desc_array[max(0, i+window[0]):i]
                left = ["***"]*(abs(window[0])-len(left))+left
                right = desc_array[i:min(len(desc_array), i+window[1])]
                right = right + ["***"]*(abs(window[1])-len(right))
                v = left+right
                v = [" "+v_+" " for v_ in v]
                vecs.append(tuple(v))
    return vecs

def convert_doc_to_vecs(doc):
    vecs = []
    desc_array = doc.lower().split()
    desc_array = [d.strip() for d in desc_array]
    window = [-3, 21]
    for i, w in enumerate(desc_array):
        left = desc_array[max(0, i+window[0]):i]
        left = ["***"]*(abs(window[0])-len(left))+left
        right = desc_array[i:min(len(desc_array), i+window[1])]
        right = right + ["***"]*(abs(window[1])-len(right))
        v = left+right
        v = [" "+v_+" " for v_ in v]
        vecs.append((w, tuple(v)))
    return vecs

def parse_word_vector(vec, regexes):
    vs = []
    for v in vec:
        _v = []
        for r in regexes:
            x = r[0].search(v) #should use search, not match
            if x==None:
                _v.append(0)
            else:
                _v.append(1)
        vs.append(tuple(_v))
    return vs

def make_regex(base_regex):
    r_out = r"((\W)("+base_regex+")(\W))"#r"((\W)("+base_regex+r")|("+base_regex+r")(\W))"
    return re.compile(r_out)

def get_vecs(keywords, window=[-5,5]):
    with open('test_cases.json','r') as f:
        data = json.load(f)
    vecs = grab_word_vectors(keywords, data, window)
    print "{} vecs".format(len(vecs))
    #build list of compiled regexes
    r_list = [(make_regex(u[0].regex), u[1]) for u in units.exported]
    r_list += [(re.compile(units.Number), 'number')]#[(make_regex(units.Number), 'number')]
    # print "Testing vectorizer"
    vos = []
    for i, vec in enumerate(vecs):
        # if i%100==0:
        #     print "On {} of {}".format(i+1, len(vecs))
        vo = parse_word_vector(vec, r_list)
        vos.append(np.array(vo))
    return vos, vecs

if __name__ == '__main__':
    with open('test_cases.json','r') as f:
        data = json.load(f)
    keywords = ["dimension","dimensions"]
    vecs = grab_word_vectors(keywords, data)
    print "{} vecs, {}".format(len(vecs), vecs[0])
    #build list of compiled regexes
    r_list = [(make_regex(u[0].regex), u[1]) for u in units.exported]
    r_list += [(make_regex(units.Number), 'number')]
    print "Testing vectorizer"
    for i, vec in enumerate(vecs):
        #if i%100==0:
        #    print "On {} of {}".format(i+1, len(vecs))
        vo = parse_word_vector(vecs[0], r_list)
    print vo
