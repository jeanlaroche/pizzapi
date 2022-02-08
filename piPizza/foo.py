import json

def saveVarsToJson(fileName,obj,name):
    with open(fileName,'w') as f:
        data = {}
        for var in dir(obj):
            val = getattr(obj,var)
            if isinstance(val,int) or isinstance(val,float) or isinstance(val,list):
                data[var] = val
        A = {name:data}
        json.dump(A,f)

def readVarsFromJson(fileName,obj,name):
    with open(fileName,'r') as f:
        data = json.load(f)
        if name not in data:
            print(f"Could not find {name} in {fileName}")
            return
        data = data[name]
        for key,val in data.items():
            setattr(obj,key,val)
    return


if __name__ == '__main__':
    class A():
        a=1
        b=2.3
        c=[1,2]
        def __init__(self):
            pass
        def foo(self):
            pass

    AA=A()
    #saveVarsToJson('foo.json',AA,"Name")
    readVarsFromJson('foo.json',AA,"Name")
    print(dir(AA))
