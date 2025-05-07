from colorama import init
from termcolor import colored
init()
import time

def pprint(text,c=""):
    strtime = time.strftime("%H:%M:%S")
    text = f"{strtime} {text}"
    if c :
        print(colored(text,c))
    else:
        print(text)
    pass

def pprint_error(msg):
    msg = mk_error_msg(msg)
    pprint(msg,"red")
    pass

def pprint_warning(msg):
    msg = mk_warning_msg(msg)
    pprint(msg,"yellow")
    pass

def pprint_info(msg):
    msg = mk_info_msg(msg)
    pprint(msg,"")
    pass

def mk_error_msg(msg):
    return '[ERROR] %s'%msg

def mk_info_msg(msg):
    return '[INFO] %s'%msg

def mk_warning_msg(msg):
    return '[WARNING] %s'%msg