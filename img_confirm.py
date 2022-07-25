from fileinput import filename
import imghdr
import json
import os
from main import DATA_PATH
from img_down import IMG_PID_LIST,IMG_PATH

NOT_AN_IMAGE_PATH = os.path.join(DATA_PATH,'log','not_an_image.json')

try:
    with open (NOT_AN_IMAGE_PATH,'r') as f:
        data_json = json.load(f)
except:
    data_json = {}
fw = open (NOT_AN_IMAGE_PATH,'w+')
if IMG_PID_LIST:
    pid_list = []
    for pid_str in IMG_PID_LIST:
        pid_list.append(int(pid_str))
    pid_list.sort()
    for pid in pid_list:
        folder_name = os.path.join(IMG_PATH,str(pid))
        file_list = os.listdir(folder_name)
        for file in file_list:
            file_name = os.path.join(folder_name,file)
            with open (file_name,'rb') as f:
                is_img = imghdr.what(f)
            if not is_img:
                err_list = data_json.get(pid)
                if err_list:
                    if file not in err_list:
                        data_json[pid].append(file)
                else:
                    data_json[pid]=[file]
json.dump(data_json,fw)
fw.close()