import time, datetime
import errno
import json

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait  # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC  # available since 2.26.0
from stem import Signal
from torrequest import TorRequest
from pymongo import MongoClient
from socket import error as SocketError
from bson.json_util import dumps
from multiprocessing import Process
from selenium import webdriver
from flask import Flask, request, jsonify

global control
tor=False
client = MongoClient('mongodb://0.0.0.0:27017/')
db = client.quora

app = Flask(__name__)


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


def log(msg,db):
    """Log `msg` to MongoDB log"""
    log_collection = db.log
    entry = {}
    entry['timestamp'] = datetime.datetime.utcnow()
    entry['msg'] = msg
    log_collection.insert(entry)


@app.route("/addUser", methods=['POST', 'GET'])
def addUser():
    if request.method == 'POST':
        req = request.form.to_dict(flat=True)
        log('Message: User added ' + str(req),db)

        print req['email']
        db.user.update(
            {'email': req['email']}, {'email': req['email'], 'password': req['password']}
            , upsert=True)
        user_data = db.user.find({}, {'email': 1, 'password': 1, '_id': 0})
        str_data = str(list(user_data)).encode('ascii')
        data = {
            'success': True,
            'status_code': '200',
            'message': 'Users List ',
            'result': str_data.replace("u'", "'")
        }
        resp = jsonify(data)
        resp.status_code = 200
        return resp
@app.route("/getLogs", methods=['POST', 'GET'])
def getLogs():
    if request.method == 'GET':
        user_data = db.log.find({}).sort('_id', -1)
        serial_data=[]
        for data in user_data:
            serial_data.append(data['msg'])
            serial_data.append(str(data['timestamp']))

        print type(serial_data)
        data = {
            'success': True,
            'status_code': '200',
            'message': 'Log List ',
            'result': serial_data
        }
        resp=json.dumps(data)

        return resp
@app.route("/addProfileLink", methods=['POST', 'GET'])
def addProfile():
    if request.method == 'POST':
        req = request.form.to_dict(flat=True)
        log('Message: Profile link added ' + str(req['profile_link']),db)
        db.profile.update(
            {'profile_link': req['profile_link']}, {'profile_link': req['profile_link']}
            , upsert=True)
        user_data = db.profile.find({}, {'profile_link': 1, '_id': 0})
        str_data = str(list(user_data)).encode('ascii')
        data = {
            'success': True,
            'status_code': '200',
            'message': 'Profile link List ',
            'result': str_data.replace("u'", "'")
        }
        resp = jsonify(data)
        resp.status_code = 200
        return resp
@app.route("/startBot", methods=['POST', 'GET'])
def startBot():
    if request.method == 'POST':
        req = request.form.to_dict(flat=True)
        p = Process(target=sub_process, args=(req,))
        p.start()
        data = {
            'success': True,
            'status_code': '200',
            'message': 'Start bot ',
            'result': []
        }
        resp = jsonify(data)
        resp.status_code = 200
        return resp
def get_reloaded_driver(tr):
    tr.reset_identity()
    service_args = [
        '--proxy=127.0.0.1:9050',  # You can change these parameters to your liking.
        '--proxy-type=socks5',  # Use socks4/socks5 based on your usage.
    ]

    if tor :
     driver = webdriver.PhantomJS(service_args=service_args)
    else:
     driver=webdriver.PhantomJS()

    return driver

def sub_process(req):
    try:
        client = MongoClient('mongodb://0.0.0.0:27017/')
        db = client.quora
        log("Message: BOT started",db)
        with TorRequest(proxy_port=9050, ctrl_port=9051, password=None) as tr:
            for profile_data in db.profile.find({}):
                for user_data in db.user.find({}):
                    print str(user_data)
                    print str(profile_data)
                    log("Message: Profile selected :"+str(profile_data['profile_link']), db)
                    log("Message: User selected :"+str(user_data['email']), db)

                    if True:
                        driver = get_reloaded_driver(tr)
                        driver.get('http://checkip.amazonaws.com/')
                        ip_data = driver.find_elements_by_xpath('/html/body/pre')[0].text
                        print ip_data
                        log("Message: Ip assigned to user "+str(user_data['email'])+" as "+ip_data, db)
                        driver.get('https://quora.com/')
                        try:
                            element = WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "header_login_text_box")))
                            log("Message: Quora  loaded sucessfully", db)

                        except TimeoutException as ex:
                            driver.save_screenshot('screenshot.png')
                            log("Fail: Quora loading failed ", db)
                            log("FailSkip: Skipping actions", db)
                            print "time out"
                            continue
                        emailField = driver.find_elements_by_class_name('header_login_text_box')[0]
                        emailField.click()
                        emailField.send_keys(user_data['email'])  # print (driver.page_source.encode('utf-8'))
                        passwordField = driver.find_elements_by_class_name('header_login_text_box')[1]
                        passwordField.click()
                        passwordField.send_keys(user_data['password'])  # print (driver.page_source.encode('utf-8'))
                        loginBtn = driver.find_elements_by_class_name('submit_button')[3]
                        loginBtn.click()
                        log("MessageInitialized: Quora login for user " + user_data['email'] + " Initialized ", db)

                        try:
                            element = WebDriverWait(driver, 100).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "PagedListFoo")))
                            log("Message: Quora login "+user_data['email']+" successful ", db)

                        except TimeoutException as ex:
                            driver.save_screenshot('screenshot.png')
                            log("Fail: Quora login failed ", db)
                            log("FailSkip: Skipping actions", db)
                            print "time out"
                            continue
                        log("MessageInitialized: Quora Profile loading initialized " + profile_data['profile_link'] + " successful ", db)
                        try:
                            driver.get(profile_data['profile_link'])
                            try:
                                element = WebDriverWait(driver, 100).until(
                                    EC.presence_of_element_located((By.CLASS_NAME, "layout_3col_center")))
                                log("Message: Quora Profile loaded " + profile_data['profile_link'] + " successful ", db)

                            except TimeoutException as ex:
                                driver.save_screenshot('screenshot.png')
                                log("Fail: Quora Profile loading failed ", db)
                                log("FailSkip: Skipping actions", db)
                                print "time out"
                                continue

                            log("MessageInitialized: Quora Up voting initialized " + profile_data[
                                'profile_link'] + " successful ", db)

                            try:
                                element = WebDriverWait(driver, 100).until(
                                    EC.presence_of_element_located((By.CLASS_NAME, "icon_action_bar-button")))
                                log("Message: Quora Upvoting initializing completed  for" + profile_data['profile_link'] + "  ", db)

                            except TimeoutException as ex:
                                driver.save_screenshot('screenshot.png')
                                log("Fail: Quora Upvoting initializing failed ", db)
                                log("FailSkip: Skipping actions", db)
                                print "time out"
                                continue

                            print driver.find_elements_by_css_selector(".icon_action_bar-button.blue_icon")[0].get_attribute('innerHTML')
                            print len(driver.find_elements_by_css_selector(".icon_action_bar-button.blue_icon"))
                            for i in xrange(0, len(driver.find_elements_by_css_selector(".icon_action_bar-button.blue_icon"))):
                                upvote = driver.find_elements_by_css_selector(".icon_action_bar-button.blue_icon")[i]
                                log("Message: Upvote post "+str(i)+"  by user " + user_data['email'] + " for profile "+profile_data['profile_link']+" successful ", db)
                                print upvote
                                if upvote.get_attribute('class').find('pressed') == -1:
                                    upvote.click()
                                    print "clicked"
                                else:
                                    print "not clicked"
                        finally:
                            log("Message: Completed actions for " + user_data['email'] + " successful ", db)
                            driver.quit()
    except SocketError as e:
        print "new error"
        if e.errno != errno.ECONNRESET:
            raise  # Not error we are looking for
        pass  # Handle error here.
if __name__ == '__main__':
    app.run(host='0.0.0.0')