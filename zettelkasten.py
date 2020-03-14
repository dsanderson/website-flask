import markdown2, re
fname = 'QuickNote.md'

def parse_id(id):
    """Convert a numeric (#.#.#...) or alphanumeric (#X#X#...) to a list"""
    cleaned = "".join(id.lower().split("."))
    if cleaned.isdecimal():
        l = id.split(".")
        l = tuple([int(i) for i in l])
    return l

def parse_title(title):
    """consume a line containing an id and extract the formatted ID, and the title"""
    t = title.strip().strip('>').strip()
    t = t.split()
    id = parse_id(t[0])
    title = " ".join(t[1:])
    return id, title

def is_id(id):
    pass

def get_parent(id):
    """"""
    pass

def zk(file):
    flat_tree = {}
    #tree = []
    with open(file, 'r') as f:
        data = f.readlines()
    #find lines that contain an ID
    regex = re.compile(r"\A\s*>\s*[\w\.]+")
    titles = []
    for i, l in enumerate(data):
        if regex.search(l) != None:
            titles.append(i)
    #glom together lines, grouped by the id
    titles = set(titles)
    title = ""
    id = ()
    content = ""
    for i, l in enumerate(data):
        if i in titles:
            flat_tree[id] = {"title":title, "content":content}
            id, title = parse_title(data[i])
            content = ""
        else:
            content = content+'\n'+data[i]
    flat_tree[id] = {"title":title, "content":content}
    #process the flat tree into the actual tree
    tree = sorted(flat_tree.keys())
    output = []
    for t in tree:
        output.append({"id":".".join([str(i) for i in t]), "title":markdown2.markdown(flat_tree[i]["title"]), "content":markdown2.markdown(flat_tree[i]["content"])})
    return output
