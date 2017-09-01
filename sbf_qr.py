import os, time, csv, io, copy

def load_companies():
    """load the list of companies, and return as a dictionary, with the keys as normalized company names, and the sign index and name after"""
    companies = []
    with open("sbff_cubes.txt", "r") as f:
        cs = f.readlines()
    cs = [c.strip().lower().strip('the').strip() for c in cs if c.strip() != ""]
    companies = companies + cs
    with open("sbf_cubes.txt", "r") as f:
        cs = f.readlines()
    cs = [c.strip().lower().strip('the').strip() for c in cs if c.strip() != ""]
    companies = companies + cs
    def sign(i):
        s = "SBFF" if i<=79 else "SBF"
        ti = i if i<=79 else i-79
        return (ti,s)
    cos = {c:sign(i) for i,c in enumerate(companies)}
    return cos

def load_qr_codes():
    qr_codes = []
    companies = load_companies()
    with open("qr_codes.csv") as f:
        reader = csv.reader(f)
        for row in reader:
            data = {"qr":int(row[0])+1000000,
                "cube":int(row[0]),
                #"sign_number":,
                #"sign":"SBFF" if int(row[0])<=79 else "SBF",
                "salutation":row[2],
                "name":row[3],
                "designation":row[4],
                "company":row[5]}
            try:
                data["sign_number"] = companies[data["company"].strip().lower().strip('the').strip()][0]
                data["sign"] = companies[data["company"].strip().lower().strip('the').strip()][1]
            except:
                data["sign_number"] = -1
                data["sign"] = "SBF"
            qr_codes.append(copy.deepcopy(data))
    qr_codes = {item["qr"]:item for item in qr_codes}
    return qr_codes

qr_codes = load_qr_codes()

def log_and_fetch(scanned_number):
    with io.open("/var/www/flask/scans.log", "a") as f:
        ts = int(time.time())
        f.write(u"{},{}\n".format(ts, scanned_number))
    try:
        return qr_codes[scanned_number]
    except KeyError:
        return {"qr":0
            "cube":0
            "sign_number":-1
            "sign":"SBF"
            "salutation":""
            "name":""
            "designation":""
            "company":""}
