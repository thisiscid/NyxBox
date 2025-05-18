import json
import os
import random
def vend_random_chall():
    with open(os.path.join("challenges", random.choice(os.listdir("challenges"))), 'r') as file:
           data = json.load(file)
           return data

def list_all_chall():
    ret=[]
    for chall in os.scandir("challenges"):
        ret.append(str(chall).replace("<DirEntry '", "").replace("'>",'').replace(".json",""))
    return ret

def list_all_chall_detailed():
    ret=[]
    for chall in os.listdir("challenges"):
         with open(os.path.join("challenges", chall), 'r') as file:
           ret.append(json.load(file))
    return ret

def return_tests(challenge):
    with open(os.path.join("challenges", challenge+".json"), 'r') as file:
        file=json.load(file)
        return file["tests"]

