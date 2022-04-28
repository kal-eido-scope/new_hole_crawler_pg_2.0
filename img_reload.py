import json
import sys
import imghdr
import os
import requests
import argparse
import copy
from img_down import get_format_path, re_find,IMG_PATH,ERROR_IMG_PATH,IMG_EXTS
from funcs import NOT_AN_IMAGE_PATH

def reload_image(error_img_log:dict):
    for pid_str,values in copy.deepcopy(error_img_log).items():
        pid = int(pid_str)
        new_values = []
        os.makedirs(os.path.join(IMG_PATH,'%0d'%pid), exist_ok=True)
        for value in values:
            img = list(value)[0]
            flag = True
            img_path = get_format_path(img,pid)
            try:
                img_get = requests.get(img,verify=False)
                status_code = img_get.status_code
            except:
                    status_code = 404
            if status_code == 200:
                with open(img_path,'wb') as f:
                    f.write(img_get.content)
                print('%d\tAn img dowloaded.'%pid)
            else:
                flag = False
                new_values.append({list(value)[0]:status_code})
                print('%d\tAn img failed.'%pid)
        if flag:
            error_img_log.pop(pid_str)
            print('%d\tAll img(s) downloaded successfully.'%pid)
        else:
            error_img_log[pid_str] = new_values
            print('%d\tSome img(s) failed to be downloaded.'%pid)
        
def recover_url(fn:str,imgs):
    for img in imgs:
        if fn in img:
            return img
    return ''
            
def reload_url(error_imgs):
    for pid_str,fns in copy.deepcopy(error_imgs).items():
        pid = int(pid_str)
        imgs = re_find(pid)
        for fn in fns:
            url = recover_url(fn,imgs)
            img_path = get_format_path(url,pid)
            try:
                img_get = requests.get(url,verify=False)
                status_code = img_get.status_code
            except:
                    status_code = 404
            if status_code == 200:
                with open(img_path,'wb+') as f:
                    f.write(img_get.content)
                with open (img_path,'rb') as f:
                    is_img = imghdr.what(f)
                if is_img:    
                    error_imgs[pid_str].remove(fn)
                    if error_imgs[pid_str]:
                        pass
                    else:
                        error_imgs.pop(pid_str)
                    print('%d\tAn img reloaded.'%pid)
            else:
                print('%d\tAn img failed to be reloaded.'%pid)

def main():
    parser = argparse.ArgumentParser('T-hole.red Img reload')
    parser.add_argument('--d', type=bool, help='Not downloaded')
    parser.add_argument('--e', type=bool, help='Not an image')
    args = parser.parse_args()
    if args.d is None and args.e is None:
        print('Nothing Activated')
    if args.d:
        try:
            with open(ERROR_IMG_PATH,'r')as f:
                error_img_log = json.load(f)
            reload_image(error_img_log)
        except Exception as e:
            print(e)
            print(e.__traceback__.tb_frame.f_globals["__file__"])
            print(e.__traceback__.tb_lineno)
            sys.exit()
        try:
            with open(ERROR_IMG_PATH,'w+')as f:
                json.dump(error_img_log,f)
        except Exception as e:
            print(e)
            print(e.__traceback__.tb_frame.f_globals["__file__"])
            print(e.__traceback__.tb_lineno)
        
    if args.e:    
        try:
            with open(NOT_AN_IMAGE_PATH,'r')as f:
                error_imgs = json.load(f)
            reload_url(error_imgs)
        except Exception as e:
            print(e)
            print(e.__traceback__.tb_frame.f_globals["__file__"])
            print(e.__traceback__.tb_lineno)
            sys.exit()
        try:
            with open(NOT_AN_IMAGE_PATH,'w+')as f:
                json.dump(error_imgs,f)
        except Exception as e:
            print(e)
            print(e.__traceback__.tb_frame.f_globals["__file__"])
            print(e.__traceback__.tb_lineno)

if __name__ == '__main__':
    main()
