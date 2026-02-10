import json
import random
import re
import requests
import datetime
import time
import wget
import threading
import os
import base64
from flask import request

import scheduleapi

setu_cooldown = {}  #格式: {用户ID: 最后调用时间}

def keyword(message, uid, gid = None):
    if message[:]=='>help':
        usage(gid)
    if message.startswith('>setu'):
        tags=r18=noai=None
        parts=message[6:].strip().split('-',3)
        if len(parts)>=1:
            for i in range(len(parts)):
                if parts[i]:
                    command=parts[i].split(' ',1)
                    if command[0]=='tag':
                        tags=parts[i].strip().split(' ')[1:]
                    elif command[0]=='r18':
                        r18=parts[i].strip().split(' ')[1]
                        if not r18.isdigit():
                            print(r18)
                            if r18=='on' or r18=='开启':
                                toggle_r18(gid,uid,True)
                            elif r18=='off' or r18=='关闭':
                                toggle_r18(gid,uid,False)
                            else: requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=错误的命令参数。'.format(gid))
                            return
                        elif r18=='1' or r18=='2':
                            if not is_r18_enabled(gid):
                                requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=本群未开启r18功能，请联系群管理员启用。'.format(gid))
                                return
                    elif command[0]=='noai':
                        noai=1
                    else:
                        print("Unknown command")
        print(f"Tags: {tags}, R18: {r18}, NoAI: {noai}")
        setu(gid,uid,tags,r18,noai)
    # if message[:]=='>hello':
    #    hhw(gid)
    if message[:]=='>antigen test':
        adt(gid,uid)
    if message[0:4]=='>cat':
        if message[:]=='>cat':
            httpcat(gid,-1)
        else:
            picid=message[5:]
            httpcat(gid,picid)    # 处理定时消息命令
    if message.startswith('>timer') or message.startswith('>定时'):
        try:
            if not check_permission(gid, uid, 1):
                requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=抱歉，只有群管理员/群主/开发者才能添加定时消息'.format(gid))
                return False
            if message.startswith('>timer'):
                parts = message[6:].strip().split(' ', 2)  # 分割成时间和消息内容
            else:
                parts = message[3:].strip().split(' ', 2)  # 分割成时间和消息内容
                
            if len(parts) >= 2:
                time_str = parts[0]  # 时间格式 HH:MM
                msg_content = parts[1]
                scheduleapi.schedule_daily_message(gid, msg_content, time_str)
                requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=已设置在每天 {1} 发送消息：{2}'.format(gid, time_str, msg_content))
            else:
                requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=格式错误，正确格式为：>定时 HH:MM 消息内容'.format(gid))
        except Exception as e:
            requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=设置定时消息失败：{1}'.format(gid, str(e)))

# 启动定时任务线程
def start_scheduler():
    # 从文件加载任务
    tasks = scheduleapi.load_tasks_from_file()
    for time_str, group_id, message in tasks:
        try:
            scheduleapi.schedule_daily_message(group_id, message, time_str, save_to_file=False)
            # print(f"已加载定时任务: {time_str} 发送到群 {group_id}")
        except Exception as e:
            print(f"加载定时任务失败: {time_str} {group_id} - {str(e)}")
    
    # 启动定时器线程
    scheduler_thread = threading.Thread(target=scheduleapi.run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    print(f"定时任务系统已启动，已加载 {len(tasks)} 个任务")

def adt(gid,uid):
    requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=测试中...'.format(gid))
    num=random.randint(1,100)
    time.sleep(3)
    if num<=82:
        requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message={1}- C{2}  T{3}  S{4} 是阴性呢'.format(gid,r'[CQ:at,'r'qq='+str(uid)+r']'+'\n','\n','\n','\n'))
    elif num<=86:
        requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message={1}  C{2}  T{3}  S{4} 无效的测试结果，可能是加少了'.format(gid,r'[CQ:at,'r'qq='+str(uid)+r']'+'\n','\n','\n','\n'))
    elif num<=90:
        requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message={1}  C{2}- T{3}  S{4} 无效的测试结果，可能是加多了'.format(gid,r'[CQ:at,'r'qq='+str(uid)+r']'+'\n','\n','\n','\n'))
    else:
        requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message={1}- C{2}- T{3}  S{4} 诶呀，你阳了'.format(gid,r'[CQ:at,'r'qq='+str(uid)+r']'+'\n','\n','\n','\n'))
def usage(gid):
    requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=使用说明请点击:https://docs.qq.com/doc/DYm1wSnVDVUJVUGtF'.format(gid))

def setu(gid,uid,tags,r18,noai):
    if gid==594936663: return
    # 如果提供了用户 ID，检查该用户是否在冷却时间内
    if uid is not None: 
        current_time = time.time()
        last_call_time = setu_cooldown.get(uid, 0)
        # 检查是否在一分钟冷却时间内
        if current_time - last_call_time < 60 and not check_permission(gid,uid,2):
            remaining = int(60 - (current_time - last_call_time))
            requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=不许涩涩！你需要再等{1}秒才能用这个功能！'.format(gid, remaining))
            return

    if tags: tag_request='&tag='+','.join(tags) if tags else ''
    else: tag_request=''
    url='https://api.lolicon.app/setu/v2?size=original&size=regular{0}&r18={1}&no_ai={2}'.format(tag_request,r18 if r18 else 0,noai if noai else 0)
    # print(url)
    menu=requests.get(url)
    if menu.json()['data']==[]:
        requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=没有找到符合要求的图片，请重试...'.format(gid))
        return
    setu_url=menu.json()['data'][0]['urls']['regular']
    setu_url=setu_url.replace(".re",".cat") # 国内反代i.pixiv.re炸了，改用通用的i.pixiv.cat
    #print(setu_url)
    # 检查URL是否有效（发送HEAD请求检查状态码）
    try:
        response = requests.head(setu_url, timeout=5)
        if response.status_code != 200:
            print(f"图片URL返回状态码: {response.status_code}")
            requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=图片似乎无法访问，请重试...'.format(gid))
            return
    except requests.exceptions.RequestException as e:
        print(f"检查图片URL时出错: {e}")
        requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=图片访问超时，请重试...'.format(gid))
        return    
    # 更新用户最后调用时间
    setu_cooldown[uid] = current_time
    msg_menu=requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message={1}'.format(gid,r'[CQ:image,'r'file='+str(setu_url)+r']'))
    msg_id=msg_menu.json()['data']['message_id']
    # print(msg_id)
    time.sleep(90)
    requests.get(url='http://127.0.0.1:5700/delete_msg?message_id={0}'.format(msg_id))

def toggle_r18(gid, uid, enable):
    """开启或关闭指定群的r18功能"""
    # 权限检查
    if not check_permission(gid, uid, 1):
        requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=抱歉，只有群管理员/群主/开发者才能修改r18设置'.format(gid))
        return False
        
    with open('kscnconfig.json', 'r') as f:
        config = json.load(f)
    
    # 确保r18_enabled_groups存在
    if 'r18_enabled_groups' not in config:
        config['r18_enabled_groups'] = []
    
    # 将gid转为字符串以便JSON存储
    gid_str = str(gid)

    print(config['r18_enabled_groups'])
    
    # 根据enable参数添加或移除群组
    if enable and gid_str not in config['r18_enabled_groups']:
        config['r18_enabled_groups'].append(gid_str)
        status_msg = "已开启"
    elif not enable and gid_str in config['r18_enabled_groups']:
        config['r18_enabled_groups'].remove(gid_str)
        status_msg = "已关闭"
    else:
        status_msg = "已经是" + ("开启" if enable else "关闭") + "状态"
    
    # 保存配置
    with open('kscnconfig.json', 'w') as f:
        json.dump(config, f, indent=4)
    
    requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=本群r18功能{1}'.format(gid, status_msg))
    return True

def hhw(gid):
    requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message=Hello, world!'.format(gid))

def httpcat(gid,picid):
    if(picid==-1):
        arr=[100,101,102,103,200,201,202,203,204,206,207,300,301,302,303,304,305,307,308,400,401,402,403,404,405,406,407,408,409,410,411,412,413,414,415,416,421,422,423,424,425,426,429,431,444,450,451,497,498,499,500,501,502,503,504,506,507,508,509,510,511,521,522,523,525,599]
        num=random.randint(0,65)
        url='https://http.cat/'+str(arr[num])
        requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message={1}'.format(gid,r'[CQ:image,'r'file='+str(url)+r']'))
    else:
        url='https://http.cat/'+str(picid)
        requests.get(url='http://127.0.0.1:5700/send_group_msg?group_id={0}&message={1}'.format(gid,r'[CQ:image,'r'file='+str(url)+r']'))

def poke(gid, uid):
    with open('kscnconfig.json','r') as f:
        config = json.load(f)
    num=random.randint(0,19)
    image_path= os.path.join(config['poke_image_folder'], f"{num}.jpg") # 使用配置文件中的图片路径
    file_url=f"file://{image_path}"
    requests.get(url='http://127.0.1:5700/send_group_msg?group_id={0}&message={1}'.format(
        gid, f'[CQ:image,file={file_url}]'))

def check_permission(gid, uid, required_level):
    """
    检查用户权限
    required_level: 0=普通用户, 1=管理员/群主, 2=开发者
    """
    # 检查开发者权限
    if required_level == 2:
        with open('kscnconfig.json', 'r') as f:
            config = json.load(f)
        if uid in config.get('superuser', []):
            return True
        
    # 检查管理员权限
    if required_level == 1:
        # 调用API获取群成员信息
        response = requests.get(f'http://127.0.0.1:5700/get_group_member_info?group_id={gid}&user_id={uid}')
        member_info = response.json()
        if member_info.get('status') == 'ok':
            role = member_info.get('data', {}).get('role', '')
            # 检查是否是群主或管理员
            if role in ['owner', 'admin']:
                return True
        
    # 普通用户权限
    return required_level == 0

def is_r18_enabled(gid):
    # 检查群组是否启用了r18功能
    with open('kscnconfig.json', 'r') as f:
        config = json.load(f)
    return str(gid) in config.get('r18_enabled_groups', [])