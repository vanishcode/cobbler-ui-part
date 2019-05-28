#! /usr/bin/env python
import xmlrpclib
import simplejson
import string
import time
import ipaddress
from flask import Flask
from flask import jsonify
from flask import request
from flask import session
import json
from os.path import join as pjoin

import cobbler.item_distro    as item_distro
import cobbler.item_profile   as item_profile
import cobbler.item_system    as item_system
import cobbler.item_repo      as item_repo
import cobbler.item_image     as item_image
import cobbler.item_mgmtclass as item_mgmtclass
import cobbler.item_package   as item_package
import cobbler.item_file      as item_file
import cobbler.settings       as item_settings
import cobbler.field_info     as field_info
import cobbler.utils          as utils

url_cobbler_api = None
remote = None
username = None
login_status = False
token = None

app = Flask(__name__)

@app.route('/login',methods = ['POST'])
def login():
	#username = request.form.get('username')
	#password = request.form.get('password')
	data = request.get_data()
	json_data = json.loads(data)
	username = json_data['username']
	password = json_data['password']
	url_cobbler_api = utils.local_get_cobbler_api_url()
	remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
	try:
		global token
		token = remote.login(username, password)
		global login_status 
		login_status = True
		if username == remote.get_user_from_token(token):
   			return jsonify({
   				"message": "login succeed",
   				"code": 0
   				})
	except:
		return jsonify({
				"message": "login failed",
				"code" : 1
				})

@app.route('/eventlog',methods = ['get'])
def eventlog():
	global login_status
	if login_status:
		return jsonify({
   			"message": "login failed",
   			"code": 1
   			})
	url_cobbler_api = utils.local_get_cobbler_api_url()
	remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
	events = remote.get_events()
	events2 = []
   	for id in events.keys():
      		(ttime, name, state, read_by) = events[id]
      		events2.append([id,time.asctime(time.localtime(ttime)),name,state])
	def sorter(a,b):
      		return cmp(a[0],b[0])
   	events2.sort(sorter)

	return jsonify(events2)

@app.route('/import_run',methods = ['post'])
def import_run():
	global login_status
  	if login_status:
    		return jsonify({
        			"message": "login failed",
        			"code": 1
        			})
  	url_cobbler_api = utils.local_get_cobbler_api_url()
  	remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
	options = {
	"name" : request.form.get("name"),
	"path" : request.form.get("path"),
	"breed" : request.form.get("breed"),
	"arch" : request.form.get("arch")
	}
	global token
	remote.background_import(option,token)

@app.route('/settings',methods = ['get'])
def get_settings():
	global login_status
  	if login_status:
    		return jsonify({
        		"message": "login failed",
        		"code": 1
        		})
  	url_cobbler_api = utils.local_get_cobbler_api_url()
  	remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
	return jsonify(remote.get_settings())

@app.route('/profiles',methods = ['get'])
def get_profiles():
	global login_status
  	if login_status:
    		return jsonify({
        		"message": "login failed",
        		"code": 1
        		})
  	url_cobbler_api = utils.local_get_cobbler_api_url()
  	remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
	return jsonify(remote.get_profiles())

@app.route('/distros',methods = ['get'])
def get_distros():
	global login_status
  	if login_status:
    		return jsonify({
        		"message": "login failed",
        		"code": 1
        		})
  	url_cobbler_api = utils.local_get_cobbler_api_url()
  	remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
	return jsonify(remote.get_distros())

@app.route('/rename',methods = ['get','post'])
def rename():
	global login_status
	data = request.get_data()
	json_data = json.loads(data)
	what = json_data['what']
	obj_name = json_data['obj_name']
	obj_newname = json_data['obj_newname']
  	if login_status:
    		return jsonify({
        		"message": "login failed",
        		"code": 1
        			})
  	url_cobbler_api = utils.local_get_cobbler_api_url()
  	remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
	if not remote.has_item(what,obj_name):
		return jsonify({
   			"message": "no such item",
   			"code": 2
   			})
	token = remote.login("cobbler","cobbler")
	obj_id = remote.get_item_handle(what,obj_name,token)
	remote.rename_item(what,obj_id,obj_newname,token)
	return jsonify({
   			"message": "rename success",
   			"code": 0
   			})

@app.route('/ks_list')
def ks_list():
	global login_status
  	if login_status:
    		return jsonify({
        		"message": "login failed",
        		"code": 1
        		})
  	url_cobbler_api = utils.local_get_cobbler_api_url()
  	remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
	global token
	ksfiles = remote.get_kickstart_templates(token)
 	ksfile_list = []
 	for ksfile in ksfiles:
     		if ksfile not in ["", "<<inherit>>"]:
         		ksfile_list.append((ksfile, ksfile, 'editable'))
	return jsonify(ksfile_list)

@app.route('/ks_edit')
def ks_edit():
	data = request.get_data()
	json_data = json.loads(data)
	ksfile_name = json_data['ksfile_name']
	global login_status
  	if login_status:
    		return jsonify({
        		"message": "login failed",
       			"code": 1
        		})
  	url_cobbler_api = utils.local_get_cobbler_api_url()
  	remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
 	token = remote.login("cobbler","cobbler")
	ksdata = ""
 	if not ksfile_name is None:
    		editable = remote.check_access_no_fail(token, "modify_kickstart", ksfile_name)
    		deleteable = not remote.is_kickstart_in_use(ksfile_name, token)
		dir_name = "/var/lib/cobbler/kickstarts"
		ksfile_name = pjoin(dir_name,ksfile_name)
    		ksdata = remote.read_or_write_kickstart_template(ksfile_name, True, "", token)
		return jsonify({
			"ksdata":ksdata,
			"code":0
		})
@app.route('/ks_save',methods=['post'])
def ks_save():
	data = request.get_data()
	json_data = json.loads(data)
	ksfile_name = json_data['ksfile_name']
	ksdata = json_data['ksdata']
	global login_status
  	if login_status:
    		return jsonify({
        		"message": "login failed",
        		"code": 1
        		})
  	url_cobbler_api = utils.local_get_cobbler_api_url()
  	remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
 	ksdata = ksdata.replace('\r\n','\n')
	ksfile_name = "/var/lib/cobbler/kickstarts/" + ksfile_name
	token = remote.login("cobbler","cobbler")
 	remote.read_or_write_kickstart_template(ksfile_name,False,ksdata,token)
 	return jsonify({
 			"message": "kickstart file save success",
 			"code": 0
 			})

@app.route('/setting_save')
def setting_save():
	data = request.get_data()
	json_data = json.loads(data)
	global login_status
  	if login_status:
    		return jsonify({
        		"message": "login failed",
        		"code": 1
        			})
  	url_cobbler_api = utils.local_get_cobbler_api_url()
  	remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
	setting_name = json_data['setting_name']
	setting_value = json_data['setting_value']
	token = remote.login("cobbler","cobbler")
	remote.modify_setting(setting_name, setting_value, token)
	return jsonify({
   			"message": "settings modify success",
   			"code": 0
   			})

@app.route('/error')
def error():
	return 'Error'
	
# def test_user_authenticated(request):
# 	global remote
# 	global username
# 	global url_cobbler_api

# 	if url_cobbler_api is None:
#     		url_cobbler_api = utils.local_get_cobbler_api_url()
# 		remote = xmlrpclib.Server(url_cobbler_api, allow_none=True)
#     		data = request.get_data()
#     		json_data = json.loads(data)
#     		username = json_data['username']
#     		password = json_data['password']
# 		if session.has_key('token') and session['token'] != '':
#     			try:
#         			if remote.token_check(session['token']):
#             				token_user = remote.get_user_from_token(session['token'])
#             				if session.has_key('username') and session['username'] == token_user:
#                 				username = session['username']
#                 				return jsonify({
#    									"message": "login success",
#    									"code": 0
#    									})
#     			except:
#         			pass
# 	return jsonify({
#    			"message": "login failed",
#    			"code": 1
#    			})
    

if __name__ == '__main__':
   	app.run(host='192.168.221.155',port = 5000,debug=True)

