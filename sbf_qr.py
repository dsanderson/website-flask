import os, time, csv, io, copy

def load_qr_codes():
    qr_codes = []
    with open("/var/www/flask/qr_codes.csv") as f:
        reader = csv.reader(f)
        for row in reader:
            data = {"qr":int(row[0]),
                "cube":int(row[0]),
                "sign_number":int(row[0]) if int(row[0])-1000000<=79 else int(row[0])-79,
                "sign":"SBFF" if int(row[0])-1000000<=79 else "SBF",
                "salutation":row[2],
                "name":row[3],
                "designation":row[4],
                "company":row[5]}
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
        return None
