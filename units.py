import re, os, sys, math

class Base_Unit():
    def __init__(self, vals):
        self.vals = vals
        self.regex = self.build_regex()
        self.compiled_regex = re.compile(self.regex)
    
    def build_regex(self):
        elems = list(self.vals)
        optional = False
        if '' in elems:
            elems.remove('')
            optional = True
        r = "|".join(elems)
        r = "(?:{})".format(r)
        if optional:
            r = r+'?'
        return r
        
    def convert(self, string):
        m = self.compiled_regex.match(string.lower())
        s = m.group(0)
        try:
            v = self.vals[s]
        except:
            ks = self.vals.keys()
            for k in ks:
                if s in k:
                    key = k
            v = self.vals[key]
        return v

class Multiply():
    def __init__(self, left, right):
        self.left = left
        self.right = right
        self.vals = {r'\*', r'\.', '-', ''}
        self.regex = self.build_regex()
        self.internal_regex = self.build_internal_regex()
        self.compiled_regex = re.compile(self.internal_regex)
        
    def build_regex(self):
        elems = list(self.vals)
        optional = ''
        if '' in elems:
            elems.remove('')
            optional = '?'
        r_left = self.left.regex
        r_right = self.right.regex
        r = "|".join(elems)
        r = r"(?:{})(?:\W)*?(?:{}){}(?:\W)*?(?:{})".format(r_left, r, optional, r_right)
        return r
    
    def build_internal_regex(self):
        elems = list(self.vals)
        optional = ''
        if '' in elems:
            elems.remove('')
            optional = '?'
        r_left = self.left.regex
        r_right = self.right.regex
        r = "|".join(elems)
        r = r"(?P<left>{})(?:\W)*?(?:{}){}(?:\W)*?(?P<right>{})".format(r_left, r, optional, r_right)
        return r
    
    def convert(self, string):
        s = string.lower()
        m = self.compiled_regex.match(s)
        l = m.group('left')
        r = m.group('right')
        res = self.left.convert(l) * self.right.convert(r)
        return res

class Divide():
    def __init__(self, left, right):
        self.left = left
        self.right = right
        self.vals = {r'per', r'\\', 'p', "by", '/'}
        self.regex = self.build_regex()
        self.internal_regex = self.build_internal_regex()
        self.compiled_regex = re.compile(self.internal_regex)
        
    def build_regex(self):
        elems = list(self.vals)
        optional = ''
        if '' in elems:
            elems.remove('')
            optional = '?'
        r_left = self.left.regex
        r_right = self.right.regex
        r = "|".join(elems)
        r = r"(?:{})(?:\W)*?(?:{}){}(?:\W)*?(?:{})".format(r_left, r, optional, r_right)
        return r
    
    def build_internal_regex(self):
        elems = list(self.vals)
        optional = ''
        if '' in elems:
            elems.remove('')
            optional = '?'
        r_left = self.left.regex
        r_right = self.right.regex
        r = "|".join(elems)
        r = r"(?P<left>{})(?:\W)*?(?:{}){}(?:\W)*?(?P<right>{})".format(r_left, r, optional, r_right)
        #print r
        return r
    
    def convert(self, string):
        s = string.lower()
        m = self.compiled_regex.match(s)
        l = m.group('left')
        r = m.group('right')
        res = self.left.convert(l) / float(self.right.convert(r))
        return res

Prefix = Base_Unit({'m':0.001, 'mil':0.001, 'milli':0.001, 'c':0.01, 'centi':0.01, 'deci':0.01, 'k':1000.0, 'kilo':1000.0, '':1.0})
Force = Multiply(Prefix,
                Base_Unit({'n':1.0, 'newton':1.0, 'lb':4.44822, 'lbf':4.44822, 'lbs':4.44822, 'pound':4.44822, "oz":0.27801385, "ounce":0.27801385}))
Mass = Multiply(Prefix,
               Base_Unit({"gram":0.001, "g":0.001, "pound":0.453592, "lb":0.453592, "lbs":0.453592, "oz":0.0283495, "ounce":0.0283495}))
Angle = Multiply(Prefix,
                Base_Unit({"radian":1.0, "rad":1.0, "revolution":2*math.pi, "rev":2*math.pi, "r":2*math.pi, "degree":0.0174533, "deg":0.0174533}))
Length = Multiply(Prefix,
                 Base_Unit({"m":1.0,"meter":1.0,"meters":1.0,"in":0.0254,"inch":0.0254,"ft":0.3048,"foot":0.3048,"yard":0.9144, '"':0.0254,"'":0.3048}))
Time = Base_Unit({"s":1.0,"second":1.0,"sec":1.0,"secs":1.0,"minute":60.0,"m":60.0,"min":60.0,"h":3600.0,"hr":3600.0,"hour":3600.0})
Money = Base_Unit({"\\$":1.0})
Voltage = Multiply(Prefix,
                   Base_Unit({"v":1.0,"volts":1.0,"volt":1.0,"voltage":1.0}))
Current = Multiply(Prefix,
                   Base_Unit({"a":1.0,"amp":1.0,"amps":1.0,"amperage":1.0}))
Torque = Multiply(Force, Length)
Speed = Divide(Length, Time)
Angular_Speed = Divide(Angle, Time)
Current_Capacity = Multiply(Current, Time)
Number = r"[-]?(?:(?:\d{1,3}(?:,\d{3})*)|(?:\d+))(?:\.\d+)?"
exported = [(Force, "force", "before"),
                  (Mass, "mass", "before"),
                  (Angle, "angle", "before"),
                  (Length, "length", "before"),
                  (Time, "time", "before"),
                  (Money, "money", "after"),
                  (Voltage, "voltage", "before"),
                  (Current, "current", "before"),
                  (Torque, "torque", "before"),
                  (Speed, "speed", "before"),
                  (Angular_Speed, "angular_speed", "before"),
                  (Current_Capacity, "current_capacity", "before")]