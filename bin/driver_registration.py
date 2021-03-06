import json, urllib, random, string
from flask import request, jsonify, render_template
from bin import app, mysql, util

############################
##### Register Driver ######
############################

#Allows a Driver to add themselves to the system by adding their
#info to the Database.
@app.route("/register_driver", methods=['POST'])
def register_driver():
    try:
        _firstName = request.get_json().get('first_name','')
        _lastName = request.get_json().get('last_name','')
        _phoneNumber = request.get_json().get('phone_number','')
        
        p_num = util.format_phone_number(_phoneNumber)
        if p_num == '':
            return jsonify({'status':"error",
                           'message':'You did not supply a valid phone number. Please try again.'})
           
        #Connect to DB, call stored proc, close is handled automatically?
        cursor = mysql.connection.cursor()
        cursor.callproc('new_driver',[_firstName, _lastName, p_num])
        data = cursor.fetchall()
        cursor.close()
        #we are not expecting any data in response except in error
        if len(data) is not 0:
            res = jsonify(data[0])
            #res = jsonify({'status':str(data[0]),
            #               'message':str(data[1])})
            mysql.connection.rollback()
        else:
            #commit changes to DB
            mysql.connection.commit()
            res = jsonify({'status':"success"})
    except Exception as e:
        res = jsonify({'status':str(e)})
    return res

############################
# Format Deregister Driver #
############################

#Checks the format of the submitted confirmation code to confirm it is valid
@app.route("/format_deregister_driver", methods=['GET','POST'])
def format_deregister_driver():
    try:
        _key = request.form.get('key')
        _conf_code = request.form.get('conf_code')
        
        
        cursor = mysql.connection.cursor()
        cursor.callproc('check_confirm_code',[_key, _conf_code])
        data = cursor.fetchall()
        cursor.close()
        
        if len(data) is 0:
            mysql.connection.rollback()
            return render_template('message.html',
                           title='Whoops',
                           hide_mobile='true',
                           message='Something went wrong, please try again.')
        elif data[0].get('status') == 'invalid':
            mysql.connection.rollback()
            return render_template('message.html',
                           title='Incorrect Code',
                           hide_mobile='true',
                           message="Incorrect confirmation code.")
        elif data[0].get('status') == 'success':
            
            mysql.connection.commit()
            id_driver = data[0].get('idDriver')
            
            cursor = mysql.connection.cursor()
            cursor.callproc('get_assoc_businesses',[id_driver])
            data = cursor.fetchall()
            cursor.close()
            mysql.connection.commit()
            
            user = {
                'key': _key,
                'conf_code': _conf_code
            }
            lines = []
            if len(data) is not 0:
                user['nickname'] = data[0].get('FirstName')
                
                for row in data:
                    if row.get('HireStatus') != 'blocked':
                        lines.append(
                            {
                                'id': row.get('idBusinessDriver'),
                                'business': row.get('BusName'),
                                'status': row.get('HireStatus')
                            }
                        )
                        
            return render_template("driver_view_deregister.html",
                           title='Deregister',
                           user=user,
                           lines=lines)
            #TODO: grab all info about businesses that have hired this driver, display in form with checkboxes
            #   Display "deregister from dispatcher as a whole" button
            
        
        
    except Exception as e:
        return render_template('message.html',
                           title='Whoops',
                           hide_mobile='true',
                           message='Something went wrong, please try again.')
    return 'end' #should never get here

############################
#### Deregister Driver #####
############################

#If confirmation code is valid, removes Driver from requested business(es)
#or from the System entirely
@app.route("/perform_deregister_driver", methods=['GET','POST'])
def perform_deregister_driver():
    try:
        #This check maintains security; valid conf_code is required
        _key = request.form.get('key')
        _conf_code = request.form.get('conf_code')
        
        cursor = mysql.connection.cursor()
        cursor.callproc('check_confirm_code',[_key, _conf_code])
        data = cursor.fetchall()
        cursor.close()
        
        if len(data) is 0:
            mysql.connection.rollback()
            return render_template('message.html',
                           title='Whoops',
                           hide_mobile='true',
                           message='Something went wrong, please try again.')
        elif data[0].get('status') == 'invalid':
            mysql.connection.rollback()
            #return render_template('message.html',
            #               title='Incorrect Code',
            #               hide_mobile='true',
            #               message="Incorrect confirmation code.")
            
            return render_template('driver_deregister.html',
                           title='Driver Signup',
                           incorrect='Incorrect Confirmation Code'
                           )
        
        
        elif data[0].get('status') == 'success':
            mysql.connection.commit()
            id_driver = data[0].get('idDriver')
            
            #consume conf_code
            cursor = mysql.connection.cursor()
            cursor.callproc('delete_confirm_code',[_key])
            data = cursor.fetchall()
            cursor.close()
            mysql.connection.commit()
            
            #build requested mods
            id_to_drop = []
            drop_all = 'all' in request.form
            for v in request.form.getlist('choices'):
                id_to_drop.append(v)
            
            sql_list = ''
            if len(id_to_drop) is not 0:
                sql_list = ','.join(map(str, id_to_drop))
            
            #execute mods
            cursor = mysql.connection.cursor()
            cursor.callproc('delete_driver',[drop_all,id_driver,sql_list])
            data = cursor.fetchall()
            cursor.close()
            mysql.connection.commit()
            
            
            #return  str(sql_list) + "|" + str(drop_all)
            return render_template('message.html',
                           title='Successful Deregistration',
                           hide_mobile='true',
                           message='You have successfuly applied the changes.')
                        

    except Exception as e:
        return jsonify({'status':str(e)})
    #return str(request.form)
    return 'end' #should never get here

############################
#### Apply To Business #####
############################
  
#Register Driver with a business    
@app.route("/apply_to_business/<unique_url>", methods=['GET','POST'])
def apply_to_business(unique_url):
    try:
        phoneNumber = request.get_json().get('phone_number','')
        
        p_num = util.format_phone_number(phoneNumber)
        if p_num == '':
            return jsonify({'status':"error",
                           'message':'You did not supply a valid phone number. Please try again.'})

        
        
        #get driver from phone number
        cursor = mysql.connection.cursor()
        cursor.callproc('get_driver_from_phone', [p_num])
        data = cursor.fetchall()
        cursor.close()

        if len(data) is 0:
            mysql.connection.rollback()
            return jsonify({'status':'error','message':'Something went wrong, please try again.'})
        mysql.connection.commit()
        id_driver = data[0].get('idDriver')
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM Driver WHERE idDriver = %s", [id_driver])
        data_driver_detail = cursor.fetchall()
        cursor.close()
        mysql.connection.commit()
        if len(data_driver_detail) is 0:
            return jsonify({'status':'error','message':'Something went wrong, please try again.'})
        
        
        
        if str(data_driver_detail[0].get('Enrolled')) == '0' or data_driver_detail[0].get('status') == 'error':
            return jsonify({'status':'error','message':'You are not registered with Dispatcher. Please register with Dispatcher before applying to a specific Merchant.'})
        

        #get business from unique_url
        cursor = mysql.connection.cursor()
        #TODO Not Correct Proc Call
        cursor.callproc('get_business_from_url', [unique_url])
        bus_data = cursor.fetchall()
        cursor.close()

        if len(bus_data) is 0:
            mysql.connection.rollback()
            return jsonify({'status':'error','message':'Something went wrong, please try again.'})
        
        id_business = bus_data[0].get('idBusiness')

        cursor = mysql.connection.cursor()
        cursor.callproc('new_business_driver', [id_driver, id_business])
        new_data = cursor.fetchall()
        cursor.close()
        mysql.connection.commit()
        if len(new_data) is 0:
            return jsonify({'status':'success','message':'You have succesfuly applied to ' + bus_data[0].get('BusName')})
        else:
            return jsonify({'status':'success','message':'You already have a relationship with ' + bus_data[0].get('BusName')})

    except Exception as e:
        return jsonify({'status':str(e)})

    return jsonify({'status':'error','message':'Something went wrong, please try again.'})
