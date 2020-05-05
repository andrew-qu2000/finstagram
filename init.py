from flask import Flask, render_template, request, session, url_for, redirect
import hashlib
import pymysql.cursors
from datetime import datetime
SALT = 'sevenoriginal'
app = Flask(__name__)

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port=3306,
                       user='root',
                       password='root',
                       db='finstagram',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

@app.route('/')
def hello():
    return render_template('index.html') 

@app.route('/login')
def login():
    return render_template('login.html')
    
@app.route('/register')
def register():
    return render_template('register.html')
    
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    username = request.form['username']
    password = request.form['password']
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM person WHERE username = %s and password = %s'
    cursor.execute(query, (username, hashed_password))
    
    data = cursor.fetchone()
    
    cursor.close()
    if(data):
        session['username'] = username
        return redirect(url_for('home'))
    else:
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    firstName = request.form['fName']
    lastName = request.form['lName']
    username = request.form['username']
    password = request.form['password']
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    email = request.form['email']
    cursor = conn.cursor()
    
    query = 'SELECT * FROM person WHERE username = %s'
    cursor.execute(query, (username))
    
    data = cursor.fetchone()
    
    if(data):
        error = "This user already exists"
        cursor.close()
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO person VALUES(%s, %s, %s, %s, %s)'
        cursor.execute(ins, (username, hashed_password, firstName, lastName, email))
        conn.commit()
        cursor.close()
        return render_template('index.html')

@app.route('/home')
def home():
    user = session['username']
    query = 'SELECT pID, postingDate FROM photo NATURAL JOIN ( SELECT pID FROM ( SELECT pID FROM photo WHERE poster IN ( SELECT followee FROM follow WHERE follower = %s AND followStatus=1 ) AND allFollowers=1 ) AS allFollowerPhotos UNION ( SELECT pID FROM sharedwith WHERE (groupName,groupCreator) IN ( SELECT groupName, groupCreator FROM belongto WHERE username = %s ) ) ) AS visiblePIDs ORDER BY postingDate DESC'
    cursor = conn.cursor()
    cursor.execute(query, (user, user))
    visiblePIDs = cursor.fetchall()
    return render_template('home.html', username=user, visiblePIDs=visiblePIDs)

@app.route('/viewPhotoInfo')
def viewPhotoInfo():
    user = session['username']
    pID = request.args['pID']
    query = 'SELECT * FROM photo WHERE pID = %s'
    cursor = conn.cursor()
    cursor.execute(query, (pID))
    data = cursor.fetchone()
    
    poster = data['poster']
    #get poster name
    query = 'SELECT firstName,lastName FROM person WHERE username = %s'
    cursor.execute(query, (poster))
    names = cursor.fetchone()
    #get tags
    query = 'SELECT username FROM tag WHERE pID = %s AND tagStatus = %s'
    cursor.execute(query, (pID, 1))
    tags = cursor.fetchall()
    #get reacts
    query = 'SELECT * FROM reactto WHERE pID = %s ORDER BY reactiontime DESC'
    cursor.execute(query, (pID))
    reacts = cursor.fetchall()
    return render_template('viewPhotoInfo.html', username=user, data=data, names=names, tags=tags, reacts=reacts)

@app.route('/postPhoto')
def postPhoto():
    username = session['username']
    return render_template('postPhoto.html')

@app.route('/postPhotoAuth', methods=['GET','POST'])
def postPhotoAuth():
    #get data about photo
    poster = session['username']
    postingDateTime = datetime.now()
    filePath = request.form['filePath']
    visibleToAll = request.form.get('allFollowers') != None
    caption = request.form['caption']
    
    cursor = conn.cursor()
    ins = 'INSERT INTO photo(postingDate, filePath, allFollowers, caption, poster) VALUES(%s, %s, %s, %s, %s)'
    
    if visibleToAll:
        cursor.execute(ins, (postingDateTime, filePath, 1, caption, poster))
        conn.commit()
        cursor.close()
        return redirect(url_for('home'))
    else:
        cursor.execute(ins, (postingDateTime, filePath, 0, caption, poster))
        conn.commit()
        pID = cursor.lastrowid
        
        query = 'SELECT groupName, groupCreator FROM belongto WHERE username=%s'
        cursor.execute(query, (poster))
        data = cursor.fetchall()
        for line in data:
            print(line)
        cursor.close()
        return render_template('chooseGroups.html', group_list=data, pID=pID)

@app.route('/chooseGroups', methods=['GET','POST'])
def chooseGroups():
    poster = session['username']
    cursor = conn.cursor()
    #get pID from url parameters
    pID = request.args['pID']
    ins = "INSERT INTO sharedWith VALUES(%s, %s, %s)"
    for groupName in request.form.keys():
        #User could belong to 2+ groups with the same name but diff creators
        creatorList = request.form.getlist(groupName)
        for creator in creatorList:
            cursor.execute(ins, (pID, groupName, creator))
        conn.commit()
    return render_template('home.html', username=poster)
    
@app.route('/makeFriendGroup')
def makeFriendGroup():
    username = session['username']
    cursor = conn.cursor()
    query = 'SELECT follower FROM follow WHERE followee = %s'
    cursor.execute(query, username)
    data = cursor.fetchall()
    return render_template('makeFriendGroup.html', friend_list = data)
    
@app.route('/makeFriendGroupAuth', methods=['GET','POST'])
def makeFriendGroupAuth():
    creator = session['username']
    groupName = request.form['groupName']
    description = request.form.get('description')
    
    cursor = conn.cursor()
    query = 'SELECT * FROM friendgroup WHERE groupName = %s AND groupCreator = %s'
    cursor.execute(query, (groupName, creator))
    data = cursor.fetchone()
    error = None
    if(data):
        error = 'You already have a group named ' + groupName
        cursor.close()
        return render_template('makeFriendGroup.html', error=error)
    else:
        ins = 'INSERT INTO friendgroup VALUES(%s, %s, %s)'
        cursor.execute(ins, (groupName, creator, description))
        conn.commit()
        ins = 'INSERT INTO belongTo VALUES(%s, %s, %s)'
        cursor.execute(ins, (creator, groupName, creator))
        conn.commit()
        friendsToBeAdded = request.form.getlist('follower')
        print(friendsToBeAdded)
        for friend in friendsToBeAdded:
            print(friend)
            cursor.execute(ins, (friend, groupName, creator))
            conn.commit()
        cursor.close()
        return render_template('home.html', username=creator)

@app.route('/addToFriendGroup')
def addToFriendGroup():
    user = session['username']
    query = 'SELECT groupName FROM friendgroup WHERE groupCreator = %s'
    cursor = conn.cursor()
    cursor.execute(query, (user))
    groups = cursor.fetchall()
    return render_template('chooseGroupToEdit.html', username=user, groups=groups)

@app.route('/addToFriendGroup2')
def addToFriendGroup2():
    user = session['username']
    groupName = request.args['groupName']
    return render_template('findUserToAdd.html', username=user, groupName=groupName)
    
@app.route('/addToFriendGroup3', methods=['GET','POST'])
def addToFriendGroup3():
    user = session['username']
    groupName = request.args['groupName']
    newFriend = request.form['newFriend']
    query = 'SELECT * FROM person WHERE username = %s'
    cursor = conn.cursor()
    cursor.execute(query, (newFriend))
    data = cursor.fetchone()
    error = None
    if(data):
        query = 'SELECT * FROM belongto WHERE username = %s AND groupName = %s AND groupCreator = %s'
        cursor.execute(query, (newFriend, groupName, user))
        data = cursor.fetchone()
        if(data):
            error = "User already in group"
            cursor.close()
            return render_template('findUserToAdd.html', username=user, groupName=groupName, error=error)
        else:
            ins = 'INSERT INTO belongto VALUES (%s, %s, %s)'
            cursor.execute(ins, (newFriend, groupName, user))
            conn.commit()
            cursor.close()
            return render_template('findUserToAdd.html', username=user, groupName=groupName)  
    else:
        error = "User does not exist"
        cursor.close()
        return render_template('findUserToAdd.html', username=user, groupName=groupName, error=error)
    
@app.route('/manageFollows')
def manageFollows():
    user = session['username']
    cursor = conn.cursor()
    query = 'SELECT * FROM follow WHERE followee = %s AND followStatus = %s'
    cursor.execute(query, (user, 0))
    incomingRequests = cursor.fetchall()
    cursor.close()
    return render_template('manageFollows.html', username=user, request_list=incomingRequests)

@app.route('/sendRequest', methods=['GET','POST'])
def sendRequest():
    user = session['username']
    followee = request.form['followee']
    query = 'SELECT * FROM person WHERE username = %s'
    cursor = conn.cursor()
    cursor.execute(query, (followee))
    data = cursor.fetchone()
    error = None
    if(data):
        query = 'SELECT * FROM follow WHERE follower = %s AND followee = %s'
        cursor.execute(query, (user, followee))
        data = cursor.fetchone()
        if(data):
            error = "Request already sent"
        else:
            ins = 'INSERT INTO follow VALUES(%s, %s, %s)'
            cursor.execute(ins, (user, followee, 0))
            conn.commit()
            return redirect('/manageFollows')      
    else:
        error = "User does not exist"
    query = 'SELECT * FROM follow WHERE followee = %s AND followStatus = %s'
    cursor.execute(query, (user, 0))
    incomingRequests = cursor.fetchall()
    cursor.close()
    return render_template('manageFollows.html', username=user, request_list=incomingRequests, error=error)
        
@app.route('/respondToRequest', methods=['GET','POST'])
def respondToRequest():
    user = session['username']
    formResponse = request.form['response'].split()
    response = formResponse[0]
    follower = formResponse[1]
    cursor = conn.cursor()
    if response=="Accept":
        update = 'UPDATE follow SET followStatus = %s WHERE followee = %s AND follower = %s'
        cursor.execute(update, (1, user, follower))
    else:
        delete = 'DELETE FROM follow WHERE followee = %s AND follower = %s'
        cursor.execute(delete, (user, follower))
    conn.commit()
    cursor.close()
    return redirect('/manageFollows')
    
@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')
    
app.secret_key = 'hopcrunch'

if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)