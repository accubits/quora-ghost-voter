import time, datetime
import errno
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
client = MongoClient('mongodb://0.0.0.0:27017/')
db = client.quora
log_collection = db.log

app = Flask(__name__)


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


def log(msg):
    """Log `msg` to MongoDB log"""
    entry = {}
    entry['timestamp'] = datetime.datetime.utcnow()
    entry['msg'] = msg
    log_collection.insert(entry)


@app.route("/addUser", methods=['POST', 'GET'])
def addUser():
    if request.method == 'POST':
        req = request.form.to_dict(flat=True)
        log('User added ' + str(req))

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
    if request.method == 'POST':
        user_data = db.log.find({}).sort('_id', -1)
        str_data = str(list(user_data)).encode('ascii')
        data = {
            'success': True,
            'status_code': '200',
            'message': 'Log List ',
            'result': str_data.replace("u'", "'")
        }
        resp = jsonify(data)
        resp.status_code = 200
        return resp
@app.route("/addProfileLink", methods=['POST', 'GET'])
def addProfile():
    if request.method == 'POST':
        req = request.form.to_dict(flat=True)
        log('Profile link added ' + str(req['profile_link']))
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
    driver = webdriver.PhantomJS(service_args=service_args)
    return driver
def sub_process(req):
    try:
        client = MongoClient('mongodb://0.0.0.0:27017/')
        db = client.quora
        with TorRequest(proxy_port=9050, ctrl_port=9051, password=None) as tr:
            for profile_data in db.profile.find({}):
                for user_data in db.user.find({}):
                    print str(user_data)
                    print str(profile_data)
                    if True:
                        driver = get_reloaded_driver(tr)
                        driver.get('http://checkip.amazonaws.com/')
                        ip_data = driver.find_elements_by_xpath('/html/body/pre')[0].text
                        print ip_data
                        driver.get('https://quora.com/')
                        try:
                            element = WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "header_login_text_box")))
                        except TimeoutException as ex:
                            log("Fail********Qurora didnt load User ip" + ip_data + " user details:" + user_data[
                                'email'] + 'upvote profile:' +
                                profile_data['profile_link'])
                            continue
                        emailField = driver.find_elements_by_class_name('header_login_text_box')[0]
                        print emailField
                        emailField.click()
                        emailField.send_keys(user_data['email'])  # print (driver.page_source.encode('utf-8'))
                        passwordField = driver.find_elements_by_class_name('header_login_text_box')[1]
                        print passwordField
                        print passwordField.click()
                        passwordField.send_keys(user_data['password'])  # print (driver.page_source.encode('utf-8'))
                        loginBtn = driver.find_elements_by_class_name('submit_button')[3]
                        print loginBtn
                        loginBtn.click()
                        try:
                            element = WebDriverWait(driver, 15).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "PagedListFoo")))
                        except TimeoutException as ex:
                            print "timeout"
                            log("FAIL:*****login" + "User ip" + ip_data + " user details:" + user_data[
                                'email'] + 'upvote profile:' +
                                profile_data['profile_link'])
                            continue
                        print "test"
                        try:
                            driver.get(profile_data['profile_link'])
                            try:
                                element = WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located((By.CLASS_NAME, "layout_3col_center")))
                                log("User ip" + ip_data + " user details:" + user_data['email'] + 'upvote profile:' +
                                    profile_data['profile_link'])
                            except TimeoutException as ex:
                                log("FAIL:*****loading profile" + "User ip" + ip_data + " user details:" + user_data[
                                    'email'] + 'upvote profile:' +
                                    profile_data['profile_link'])
                                print "time out"
                                continue
                            for i in xrange(0, len(driver.find_elements_by_class_name('Upvote'))):
                                upvote = driver.find_elements_by_class_name('Upvote')[i]
                                if upvote.get_attribute('class').find('pressed') == -1:
                                    upvote.click()
                                    print "clicked"
                                else:
                                    print "not clicked"
                        finally:
                            driver.quit()
    except SocketError as e:
        print "new error"
        if e.errno != errno.ECONNRESET:
            raise  # Not error we are looking for
        pass  # Handle error here.
if __name__ == '__main__':
    app.run(host='0.0.0.0')