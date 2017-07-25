#! /usr/bin/env python3
# -*- coding: utf-8 -*-

'''
@file: main.zhihu

@email: 412425870@qq.com

@author: Cay

@pythonVersion: Python3.6

@function: Simulate the program which can log in the http://www.zhihu.com and list the topics.

@version: v1.1

@question:
            遗留问题：
        1、频繁登录知乎网站，会使用验证码，暂时无法在登录的时候，一次性获取验证码
'''

from configparser import ConfigParser
import json
from bs4 import BeautifulSoup
import requests
import math
import re


zhihu_url = 'http://www.zhihu.com'  # index
zhihu_url_phone = zhihu_url + '/login/phone_num'  # for signining by phone_num
zhihu_url_email = zhihu_url + '/login/email'  # for signining by email
zhihu_url_captcha = zhihu_url + '/captcha.gif'  # for catching captcha.gif


class LoginException(ValueError):
    def __init__(self, errorMsg=None):
        super().__init__(self)
        self._errorMsg = errorMsg
        
    def __str__(self):
        return self._errorMsg
    
    __repr__ = __str__
    
class IniValueError(LoginException):
    pass

class ZhiHu:
    '''
        Read the properties from ini_file , and initialize the object.
    '''
    def __init__(self):
        cf = ConfigParser()
        cf.read('account.ini', 'utf-8')
        d = dict(cf.items('account'))
        self.phone = d.get('phone')
        self.email = d.get('email')
        self.password = d.get('password')
        self.topics = []
        
        self._headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv:47.0) Gecko/20100101 Firefox/47.0',
                   'Host':'www.zhihu.com',
                   'Referer':'https://www.zhihu.com/'
                   }
        self.session = None
        self._xsrf = self.get_xsrf()  # catch the xsrf for post
#         print(self._xsrf)
            
    '''
        Log in the index.
    '''            
    def login(self):
        flag = False
        data = {
                '_xsrf':self._xsrf,
                'password' : self.password
        }
        
        '''
            Check the phone or email.
        '''
        if self.phone is None and self.email is None:
            raise IniValueError('使用手机号或者邮箱登录')
        
        elif self.phone is not None:
            m = re.match(r'^\d{11}$', self.phone)
            if m:
                data['phone_num'] = self.phone
                zhihu_login_url = zhihu_url_phone
                flag = True
            else:
#                 raise ValueError('手机号码不正确')
                pass
                
        if flag is False:  # 如果手机号码格式错误，就匹配邮箱
            if self.email is not None:
                m = re.match(r'^\d*@(qq|163|gmail|126).(com|cn|org)$', self.email)
                if m:
                    data['email'] = self.email
                    zhihu_login_url = zhihu_url_email
                    flag = True
            else:
                raise IniValueError('手机号或邮箱格式不正确')

        text = self.get_response_text(zhihu_login_url, bGet=False, data=data)  # post
        print(text)
        target = json.loads(text)
        print(target)
        r = target['r']  # error code
        
        '''
            Following code has some bugs.
        '''
        if r == 1:  # failure
            if target['data']['name'] == 'ERR_VERIFY_CAPTCHA_SESSION_INVALID':  # 需要输入验证码
                response = self.session.get(zhihu_url_captcha, headers=self._headers, stream=True)
                with open('captcha.gif', 'wb') as f:
                    f.write(response.content)
            captcha = input('验证码为：')
#             print(captcha)
            data['captcha'] = captcha
            
            text = self.get_response_text(zhihu_login_url, bGet=False, data=data)  # post
            target = json.loads(text)
            if target['r'] == 1:
                raise LoginException('登录失败')
            print(target)
        else:  # success
            print('恭喜你，' + target['msg'] + '!')
            pass
    
    '''
        Function for getting the xsrf.
    '''
    def get_xsrf(self):
        self.session = requests.session()
        text = self.get_response_text(zhihu_url)

        # 等价于
        # response = requests.get(zhihu_url, headers = self._headers)
        
        soup = BeautifulSoup(text, 'html.parser')
        _xsrf = soup.find('input', attrs={'type':'hidden', 'name':'_xsrf'})['value']
        return _xsrf
    
    
    '''
        Get the html text.
    '''
    def get_response_text(self, url=None, bGet=True, data=None):
        if bGet:
            return self.session.get(url, headers=self._headers).text
        else:
            return self.session.post(url, data=data, headers=self._headers).text
    
    '''
        List the topics.
    '''
    def list_topics(self):
        text = self.get_response_text(zhihu_url)
#         print(response.text)
        soup = BeautifulSoup(text, 'html.parser')
        top = soup.find('a', attrs={'class':'zu-top-nav-userinfo '})
        href = top['href']
#         print(href)  #/people/***
        
#       soup = BeautifulSoup(str(top), 'html.parser')
#       name = re.match(r'<span.*?>(.*?)</span>', str(soup.find('span' , attrs={'class':'name'})), re.S).group(1)
#       print(name)
        name = soup.find('span', attrs={'class':'name'}).get_text()
#         print(name)  # zhihu name
        
        text = self.get_response_text(zhihu_url + href)
        soup = BeautifulSoup(text, 'html.parser')
#       print(soup.find_all('strong')[4].get_text())
        topics_num = int(re.match(r'^(\d+).*?$', soup.find_all('strong')[4].get_text(), re.S).group(1))
        print(name + '一共关注了' + str(topics_num) + '个话题')
        
        '''
            continue...
        '''
        print('分别为:')  # partial
        group = math.ceil(topics_num / 20)
        
        topics_url = zhihu_url + href + '/topics'
#         self._headers['Referer'] = topics_url
        self._headers['X-Xsrftoken'] = self._xsrf
#         self._headers['X-Requested-With'] = 'XMLHttpRequest'
        self._headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        
        for i in range(group):
            self.sub_list_topics(topics_url, i)
        
        self._headers.pop('X-Xsrftoken')  # must
#         self._headers.pop('X-Requested-With')
        self._headers.pop('Content-Type')  # for encoding:utf-8
        
        for num, topic in enumerate(self.topics):
            print(num + 1, ": " , topic)
        
        
    def sub_list_topics(self, url, index):
        if index == 0:
            # first
            text = self.get_response_text(url)
            soup = BeautifulSoup(text, 'html.parser')
            topics = soup.find('div', attrs={'id':'zh-profile-topic-list'}).find_all('strong')
            for t in topics:
                self.topics.append(t.get_text())
              
        else:
            # others
            text = json.loads(self.get_response_text(url, bGet=False, data={'start':'0', 'offset':str(20 * index)}))['msg'][1]
            # print(text)
        
            soup = BeautifulSoup(text, 'html.parser')
            topics_div = soup.find_all('div', attrs={'class':'zm-profile-section-item zg-clear'})
            for topics_node in topics_div:
                soup = BeautifulSoup(str(topics_node), 'html.parser')
                topics = soup.find_all('strong')
                for t in topics:
                    self.topics.append(t.get_text())
        
        
    '''
        Main code.
    '''
if __name__ == '__main__':
    try:
        zhihu = ZhiHu()
        zhihu.login()
        zhihu.list_topics()
    except IniValueError as iniError:
        print(iniError, ',请重新检查配置文件...')
    except LoginException as loginError:
        print(loginError, ',登录失败...')
    except ValueError as error:
        print(error)
