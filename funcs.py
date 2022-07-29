import argparse
import json
import requests
import os
from tqdm import tqdm
import sys
from time import sleep

DATA_PATH = os.path.join(os.path.dirname(__file__), 'data') #data文件夹路径
JSON_PATH = os.path.join(DATA_PATH,'json')                  #json文件夹路径
JSON_PID_LIST = os.listdir(JSON_PATH)                       #json文件夹下pid.json的list
LOG_PATH = os.path.join(DATA_PATH,'log')                    #log文件夹路径
ERROR_JSON_PATH = os.path.join(LOG_PATH,'error_json.json')  #json错误日志路径
NOT_AN_IMAGE_PATH = os.path.join(LOG_PATH,'not_an_image.json')

API_ROOT = 'https://t-hole.red/_api/v1/'
SPACE = 1200
TOKEN = '39fzRQwSVvkB3x1P'
#PROXY = {'http':'123.56.231.232'}
HEADERS = {'User-Token':TOKEN}

def template_error(pid:int,msg:str,comments:list)->str:
    """返回意外丢失模板"""
    #temp = '{"code": 0,"data": {"allow_search": false,"attention": 0,"author_title": null,'+\
    #        '"blocked": false,"can_del": false,"comments": [],"cw": null,"likenum": 0,'+\
    #        f'"pid": {pid},'+'"poll": null,"reply": 0,"text": "Not Found","timestamp": 0,"type": "text","url": null}'+'}'
    #temp = """{"code": -1,"data": {"allow_search": true,"attention": false,"author_title": null,"blocked": false,"blocked_count": null,"can_del": false,"""+\
     #   """"comments": null,"create_time": "1970-01-01T08:00:00.000000Z","cw": null,"hot_score": null,"is_blocked": false,"is_reported": null,"is_tmp": false,"""+\
      #  """"last_comment_time": "1970-01-01T08:00:00.000000Z","likenum": 0,"n_attentions": 0,"n_comments": 0,"pid": %d,"poll": null,"reply": 0,"text": "%s","timestamp": 0}}"""%(pid,msg)
    comment = ""
    if comments:
        if comments['code'] == 0:
            comment_list = []
            timestamp = 0
            attention = comments['attention']
            likenum = comments['likenum']
            n_attentions = comments['n_attentions']
            n_comments = len(comments)
            reply = n_comments
            if n_comments > 0:
                for x in comments['data']:
                    temp_comment = '{'
                    key_value = []
                    for key,value in x.items():
                        if type(value) is str:
                            temp = value.replace('\n','')
                            key_value.append('"'+str(key)+'": "'+str(temp).strip()+'"')
                        elif value is None:
                            key_value.append('"'+str(key)+'": '+'null')
                        else:
                            if type(value) is bool:
                                key_value.append('"'+str(key)+'": '+str(value).lower())
                            else:
                                key_value.append('"'+str(key)+'": '+str(value))
                    temp_comment += ','.join(key_value)
                    temp_comment += '}'
                    comment_list.append(temp_comment)
                    timestamp = max(timestamp,x['timestamp']) 
                comment = ','.join(comment_list)
    else:
        attention = 'false'
        timestamp = '0'
        likenum = '0'
        n_attentions = '0'
        n_comments = 0
        reply = 0
    temp = '''{"code": -1,"data":{"allow_search": false,"attention": %s,"author_title": null,"blocked": null,"blocked_count": null,"can_delete": false,"comments": ['''%str(attention).lower() +\
            comment +\
            '''],"create_time": 0,"cw": null,"hot_score": null,"is_blocked": false,"is_reported": null,"is_tmp": false,"last_comment_time": %s,'''%(timestamp) + \
            '''"likenum": %s,"n_attentions": %s,"n_comments": %d,"pid": %s,"poll": null,"reply": %d,"text": "%s","timestamp": 0}}'''%(likenum,n_attentions,n_comments,str(pid),reply,msg)
    return temp

def write_error(pid:int,status_code:int,data_json:dict)->bool:
    """写入错误代码，返回是否已存在，避免删除后覆盖"""
    error_code = data_json.get(pid)
    exist = True if error_code else False
    data_json[pid]=status_code
    return exist

def get_comment(pid:int)->list:
    """获取评论"""
    GET_COMMENT_URL = API_ROOT + '/getcomment?pid=' + str(pid)
    r = requests.get(GET_COMMENT_URL,headers=HEADERS)
    sleep(0.5)
    w = r.json()
    if w['code'] == -1:
        print('comment code is -1')
        return {}
    else:
        return w
def comment_process(comment:dict,cur_comments:list)->list:
    flag = True
    for cur_comment in cur_comments:
        if comment['timestamp'] == cur_comment['timestamp']:
            if comment['text'] == cur_comment['text']:
                if comment['name_id'] == cur_comment['name_id']:
                    flag = False#if comment.get('pid'):  #判断新旧版本标准，存在则采用新版本
    if flag:
        new_version = {
                "author_title": comment['author_title'],
                "blocked": comment['blocked'],
                "blocked_count": 0,
                "can_del": comment['can_del'],
                "cid": -1,
                "create_time": comment['timestamp'],
                "is_blocked": False,
                "is_tmp": False,
                "name_id": comment['name_id'],
                "text": comment['text'],
                "timestamp": comment['timestamp']
            }
        cur_comments.append(new_version)
        print('one old comment has been modified and added')
    return cur_comments

def renew_content(r:requests.Response,pid:int,post_path:str,data_json:dict):
    """更新json文件"""
    req = r.json()
    comments_req = get_comment(pid)
    if comments_req:
        comments = comments_req['data']
    if req['code']==-1: #错误
        if not os.path.exists(post_path):   #错误且之前不存在则写入
            with open (post_path,'w',encoding='utf-8') as f:
                f.write(template_error(pid,req['msg'],comments_req))
        else:
            pass    #已存在则不覆盖
        return 200
    else:
        if not os.path.exists(post_path):
            #本地不存在则直接考虑写入
            if req['data']['comments'] is None and req['data']['n_comments']>0:
                # 响应无评论且本应有评论
                if comments:#comment请求有回复则输入
                    req['data']['comments'] = comments
                else:
                    write_error(pid,r.status_code,data_json)    #写入错误代码
            elif req['data']['comments'] and len(req['data']['comments'])<req['data']['n_comments']:
                #响应有评论且本应更多
                req['data']['comments'] = comments  #取较多者
            #处理后写入文件
            os.makedirs(os.path.dirname(post_path), exist_ok=True)
            with open(post_path,'wb+') as f:    #写入文件
                f.write(json.dumps(req,ensure_ascii=False).encode('utf8'))
            return r.status_code

        else:   
            #已存在则将合并新旧评论，待插入举报恢复情况？？？
            cur_comments = req['data']['comments'] if req['data']['comments'] else comments
            with open(post_path,'r',encoding='utf-8') as f:
                past_version = json.load(f)
            if past_version['data']['comments']:
                for comment in past_version['data']['comments']:
                    cur_comments = comment_process(comment,cur_comments)
            else:
                req['data']['comments'] = cur_comments
            req['data']['comments'] = sorted(cur_comments,key = lambda x:x['cid'])
            with open(post_path,'wb+') as f:
                f.write(json.dumps(req,ensure_ascii=False).encode('utf8'))
        return r.status_code

def get_content(pid:int,s:requests.Session,data_json:dict)->int:
    """获取内容"""
    GET_URL = API_ROOT + '/getone?pid=' + str(pid)
    post_path = os.path.join(DATA_PATH, 'json','%06d.json'%pid)
    r = s.get(GET_URL,headers=HEADERS)
    sleep(0.5)
    if r.status_code != 200:
    #异常情况
        if r.status_code == 429:
            #请求过多
            sys.exit('Too many requests!')
        exist_flag = write_error(pid,r.status_code,data_json)
        if not exist_flag:
            #不在错误列表中
            if f'{pid}.json' not in JSON_PID_LIST:
                with open (post_path,'w',encoding='utf-8') as f:
                    f.write(template_error(pid,'Unknown error',[]))
        return r.status_code
    else:
        return renew_content(r,pid,post_path,data_json)

def get_cur_pid()->int:
    json_list = []
    for file_name in os.listdir(JSON_PATH):
        json_list.append(int(os.path.splitext(file_name)[0]))
    if json_list:
        json_list.sort()
        return json_list[-1]
    else:
        return SPACE+1

def get_max_pid()->int:
    """获取最新id"""
    GET_PAGE = API_ROOT + '/getlist?p=1&order_mode=0'
    r = requests.get(GET_PAGE,headers=HEADERS)
    max_pid = r.json()['data'][0]['pid']
    try:
        max_pid = r.json()['data'][0]['pid']
        return int(max_pid)
    except:
        return 100000

def process_start_end(start:int,end:int,mp:int)->tuple:
    """返回开始项和结束项"""
    if start:
        if start >= mp:
            return mp-SPACE,mp
        if end:
            if end >= mp:
                return start,mp
            else:
                if end <= start:
                    start,end = end,start
                return start,end
        else:
            return start,mp
    else:
        cur_pid = get_cur_pid()    
        return cur_pid,min(cur_pid+SPACE,mp)

def scan_mode(mp:int,scan_mode:int)->tuple:
    """扫描模式,0为从已有条目开始更新至最新条目,1为最新SPACE条,2为定期扫描(未完成)"""
    if scan_mode == 1:
        return (mp-SPACE,mp)
    elif scan_mode == 2:
        with open(os.path.join(LOG_PATH,'log.json'),'r')as f:
            dat = json.load(f)
        crawl_last = dat['crawl_last']
        return process_start_end(crawl_last,mp,mp)
    elif scan_mode == 3:
        with open(os.path.join(LOG_PATH,'log.json'),'r')as f:
            dat = json.load(f)
        crawl_last = dat['crawl_last']
        return process_start_end(1,crawl_last+1,mp)
    elif scan_mode == 4:
        return process_start_end(1,mp,mp)
    else:
        return process_start_end(None,None,mp)

def main():
    parser = argparse.ArgumentParser('New T-Hole Crawler')
    parser.add_argument('--token',type=str,help='token')#, required=True
    parser.add_argument('--start', type=int, help='Inclusion')#, required=True
    parser.add_argument('--end', type=int , help='Exclusion') #, required=True
    parser.add_argument('--scan', type=int , help='Scan Mode') #, required=True
    args = parser.parse_args()
    s = requests.Session()
    #max_pid = get_max_pid()    #获取最新id
    max_pid = 86554
    try:
        with open (ERROR_JSON_PATH,'r') as f:
            data_json = json.load(f)    #载入错误列表
    except:
        data_json = {}
    f = open (ERROR_JSON_PATH,'w+')     #打开错误列表写入状态
    try:
        start_id,end_id = scan_mode(max_pid,args.scan) if args.scan else process_start_end(args.start,args.end,max_pid)
        #start_id,end_id = 29997,max_pid
        for pid in tqdm(range(start_id,end_id), desc='Posts'):
            st_code = get_content(pid,s,data_json)
            tqdm.write(f'Request post:{pid},status_code:{st_code}')
        json.dump(data_json,f)
    except Exception as e:
        json.dump(data_json,f)          #意外错误恢复错误列表
        print(e)
        print(e.__traceback__.tb_frame.f_globals["__file__"])
        print(e.__traceback__.tb_lineno)
    f.close()

if __name__ == '__main__':
    main()
